import os
import glob
from pprint import pprint
import sys
from bs4 import BeautifulSoup
from multiprocessing import Pool, cpu_count
import argparse
import logging
from langchain_core.documents.base import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

def extract_metadata(soup, file_path):
    metadata = { 'source': None, 'title': None, 'description': None, 'language': None }
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
    else:
        metadata['description'] = metadata['title']
    # extract source
    metadata['source'] = "https://docs.openvino.ai/" + file_path
    return metadata

def extra_page_content(soup, metadata):
    main_tag = soup.find('main')
    if main_tag:
        text = main_tag.get_text()
        doc = Document(page_content=text, metadata=metadata)
        # text_splitter = RecursiveCharacterTextSplitter(
        #     chunk_size=1000, chunk_overlap=200, add_start_index=True
        # )
        # all_splits = text_splitter.split_documents(doc)
        # pprint(all_splits)
        pprint(doc)


def read_and_parse_html(file_path):
    document = None
    metadata = { 'source': None, 'title': None, 'description': None, 'language': None }
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    soup = BeautifulSoup(content, 'html.parser')
    metadata = extract_metadata(soup, file_path)
    page = extra_page_content(soup, metadata)


    #pprint(metadata)

    #logging.info(f'{soup.html}')
    #main_section = soup.find('main')

    return soup.get_text()  # Extracts text from HTML

def process_directory(directory_path):
    html_files = glob.glob(os.path.join(directory_path, '**/*.html'), recursive=True)
    logging.info(f"Total count of HTML files: {len(html_files)}")
    
    if len(html_files) == 0:
        logging.error(f"No html files found.")
        sys.exit(1)

    parsed_texts = []

    num_processes = min(len(html_files), cpu_count())
    logging.info(f"Leveraging pool of processes: {num_processes}")

    with Pool(processes=num_processes) as pool:
        parsed_texts = pool.map(read_and_parse_html, html_files)

    return parsed_texts

def main():
    logging.basicConfig(format='%(asctime)s | %(levelname)s: %(message)s', level=logging.NOTSET)

    parser = argparse.ArgumentParser(description='Process a directory of HTML files recursively utilizing max cores in parallel.')
    parser.add_argument('--dir', default='2023.3', type=str, help='Path to the directory containing HTML files (default: 2023.3)')

    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        logging.error(f"The specified directory \"{args.dir}\" does not exist.")
        sys.exit(1)

    logging.info(f"Detected num of CPU Cores: {cpu_count()}")
    parsed_texts = process_directory(args.dir)
    #print("Parsed texts:", parsed_texts)

    # Next steps: Generate embeddings and store them in the vector database

if __name__ == '__main__':
    main()