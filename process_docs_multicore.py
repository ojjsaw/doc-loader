import datetime
import json
import os
import glob
from pprint import pprint
import sys
from bs4 import BeautifulSoup
from multiprocessing import Pool, cpu_count
import argparse
import logging
from langchain_core.documents.base import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter, SpacyTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.chroma import Chroma
from tqdm import tqdm
from transformers import AutoModel
import time
import warnings
from chromadb.config import Settings

def format_duration(duration):
    """Format the duration into a human-readable string (seconds, minutes, or hours)."""
    if duration < 60:
        return f"{duration:.2f} seconds"
    elif duration < 3600:
        minutes = duration / 60
        return f"{minutes:.2f} minutes"
    else:
        hours = duration / 3600
        return f"{hours:.2f} hours"
    
def extract_metadata(soup, file_path, dir_path):
    metadata = {}
    # extract language
    html_tag = soup.find('html')
    if html_tag and html_tag.has_attr('lang'):
        metadata['language'] = html_tag['lang']
    # extract title
    title_tag = soup.title
    if title_tag:
        metadata['title'] = title_tag.get_text()
        # extract description
        description_tag = soup.find('meta', attrs={'name': 'description'})
        if description_tag and description_tag.has_attr('content'):
            metadata['description'] = description_tag['content']
        
    # extract source
    # metadata['source'] = "https://docs.openvino.ai/" + file_path
    metadata['source'] = file_path.replace(dir_path, "https://docs.openvino.ai")
    return metadata

def read_and_parse_html(task):
    file_path, dir_path = task
    doc = Document(page_content="", metadata={})
    metadata = { 'source': None, 'title': None, 'description': None, 'language': None }
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    soup = BeautifulSoup(content, 'html.parser')
    metadata = extract_metadata(soup, file_path, dir_path)
    if metadata:
        main_tag = soup.find('main')
        if main_tag:
            text = main_tag.get_text()
            text = ''.join([line+'\n' for line in text.splitlines() if line != '']) # Remove empty lines

            # with open("before.txt", 'w', encoding='utf-8') as file:
            #     file.write(text)
            # result_lines = []
            # split_lines = text.splitlines(keepends=True)
            # # print(len(split_lines))
            # for i in range(len(split_lines)):
            #     if i == len(split_lines) - 1 or split_lines[i] != split_lines[i + 1]:
            #         result_lines.append(split_lines[i])
            # text = ''.join(result_lines)
            # print(len(result_lines))
            # with open("after.txt", 'w', encoding='utf-8') as file:
            #     file.write(text)

            doc = Document(page_content=text, metadata=metadata)
    return doc

def indexing_load(args):
    html_files = glob.glob(os.path.join(args.dir, '**/*.html'), recursive=True)
    logging.info(f"HTML files: {len(html_files)}")
    
    if len(html_files) == 0:
        logging.error(f"No html files found.")
        sys.exit(1)

    num_processes = min(len(html_files), cpu_count())
    logging.info(f"Allocated processes: {num_processes}")

    # with Pool(processes=num_processes) as pool:
    #     result_docs = pool.map(read_and_parse_html, html_files)

    tasks = [(html_file, args.dir) for html_file in html_files]

    with Pool(processes=num_processes) as pool:
        result_docs = []
        for result in tqdm(pool.imap(read_and_parse_html, tasks), total=len(html_files)):
            result_docs.append(result)

    # Filter out invalid page_contents
    docs = [doc for doc in result_docs if doc.page_content != ""]
    return docs

def indexing_split(docs, args):
    ############ TODO: Experiment Other Splitters

    if args.splitter == "RecursiveCharacterTextSplitter":
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=args.csize, chunk_overlap=args.coverlap, add_start_index=True
            )
    else:
        text_splitter = SpacyTextSplitter(
            chunk_size=args.csize, 
            chunk_overlap=args.coverlap,
            pipeline=args.splitter,
            max_length=10000000
        )
        
    return text_splitter.split_documents(docs)

def indexing_embeddings(args):
    # trust_remote_code error workaround
    model = AutoModel.from_pretrained(args.emodel, trust_remote_code=True)
    ############ TODO: Experiment Other embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name = args.emodel,
        model_kwargs = {'device':'cpu'},
        encode_kwargs = {'normalize_embeddings': True}
    )
    return embeddings

def indexing_embedding_vectorstore(split_docs, embeddings, args):
    ############ TODO: Experiment Other vectorstores
    start_time = time.time()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = f"VectorStores/{timestamp}"
    Chroma.from_documents(
        documents=split_docs, 
        embedding=embeddings, 
        persist_directory=dir_name,
        client_settings=Settings(anonymized_telemetry=False)
        )
    end_time = time.time()
    duration = end_time - start_time
    logging.info(f"Chroma store duration: {format_duration(duration)}")
    return dir_name


def main():
    logging.basicConfig(format='%(asctime)s | %(levelname)s: %(message)s', level=logging.INFO)
    warnings.filterwarnings("ignore")

    parser = argparse.ArgumentParser(description='Process a directory of HTML files recursively utilizing max cores in parallel.')
    parser.add_argument('--dir', default='ov-docs', type=str, help='Path to the dir containing HTML ov-docs/2023.3/* (default: ov-docs)')
    parser.add_argument('--csize', default=1000, type=int, help='chunk size for splitting (default: 1000)')
    parser.add_argument('--coverlap', default=100, type=int, help='chunk overlap for splitting (default: 100)')
    parser.add_argument('--emodel', default='jinaai/jina-embeddings-v2-base-en', type=str, help='embeddings model string (default: jinaai/jina-embeddings-v2-base-en)')
    parser.add_argument('--splitter', default='en_core_web_trf', type=str, help='splitter types: [spaCy] en_core_web_sm, en_core_web_trf or RecursiveCharacterTextSplitter (default: en_core_web_trf)')

    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        logging.error(f"The specified directory \"{args.dir}\" does not exist.")
        sys.exit(1)

    for arg in vars(args):
        logging.info(f"{arg}: {getattr(args, arg)}")

    logging.info(f"Available CPU Cores: {cpu_count()}")
    docs = indexing_load(args)
    
    #logging.debug(f"Example doc: {docs[0]}")
    logging.info(f"Docs before split: {len(docs)}")
    split_docs = indexing_split(docs, args)
    logging.info(f"Docs after split: {len(split_docs)}")
    embeddings = indexing_embeddings(args)
    logging.info(f"Loaded embeddings: {args.emodel}")
    dir_path = indexing_embedding_vectorstore(split_docs, embeddings, args)
    logging.info(f"Completed vector store with embeddings.")

    with open(dir_path + "/process_docs_config.json", "w") as file:
        json.dump(vars(args), file)
    # Next steps: Generate embeddings and store them in the vector database

if __name__ == '__main__':
    main()