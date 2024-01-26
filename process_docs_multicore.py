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

def extract_with_delimiters(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Define your own delimiters or markers
    code_block_delimiter = "\n<code>\n{}\n</code>\n"
    heading_delimiter = "\n<heading level={level}>\n{}\n</heading>\n"

    # Initialize the result text
    result_text = ""

    for element in soup.body.find_all(recursive=False):
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # Handling headings
            level = element.name[1]  # Extract level number from tag name
            result_text += heading_delimiter.format(element.get_text(strip=True), level=level)
        elif element.name == 'pre' and element.code:
            # Handling code blocks
            result_text += code_block_delimiter.format(element.code.get_text(strip=True))
        else:
            # Handling other elements
            result_text += element.get_text(strip=True) + "\n"
    
    return result_text

def extract_metadata(soup, file_path):
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
    else:
        metadata['description'] = metadata['title']
    # extract source
    metadata['source'] = "https://docs.openvino.ai/" + file_path
    return metadata

def read_and_parse_html(file_path):
    doc = Document(page_content="", metadata={})
    metadata = { 'source': None, 'title': None, 'description': None, 'language': None }
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    soup = BeautifulSoup(content, 'html.parser')
    metadata = extract_metadata(soup, file_path)
    if metadata:
        main_tag = soup.find('main')
        if main_tag:
            text = main_tag.get_text()

            with open("before.txt", 'w', encoding='utf-8') as file:
                file.write(text)

            result_lines = []
            split_lines = text.splitlines(keepends=True)
            print(len(split_lines))
            for i in range(len(split_lines)):
                if i == len(split_lines) - 1 or split_lines[i] != split_lines[i + 1]:
                    result_lines.append(split_lines[i])
            text = ''.join(result_lines)
            print(len(result_lines))

            with open("after.txt", 'w', encoding='utf-8') as file:
                file.write(text)

            doc = Document(page_content=text, metadata=metadata)
    return doc

def process_directory(directory_path):
    html_files = glob.glob(os.path.join(directory_path, '**/*.html'), recursive=True)
    logging.info(f"Total count of HTML files: {len(html_files)}")
    
    if len(html_files) == 0:
        logging.error(f"No html files found.")
        sys.exit(1)

    num_processes = min(len(html_files), cpu_count())
    logging.info(f"Leveraging pool of processes: {num_processes}")

    with Pool(processes=num_processes) as pool:
        result_docs = pool.map(read_and_parse_html, html_files)

    # Filter out invalid page_contents
    docs = [doc for doc in result_docs if doc.page_content is not ""]
    logging.info(f"Total Documents: {len(docs)}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, add_start_index=True
        )
    return text_splitter.split_documents(docs)

def main():
    logging.basicConfig(format='%(asctime)s | %(levelname)s: %(message)s', level=logging.NOTSET)

    parser = argparse.ArgumentParser(description='Process a directory of HTML files recursively utilizing max cores in parallel.')
    parser.add_argument('--dir', default='2023.3', type=str, help='Path to the directory containing HTML files (default: 2023.3)')

    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        logging.error(f"The specified directory \"{args.dir}\" does not exist.")
        sys.exit(1)

    logging.info(f"Detected num of CPU Cores: {cpu_count()}")
    split_docs = process_directory(args.dir)
    logging.info(f"Total Documents after Splitting: {len(split_docs)}")

    # Next steps: Generate embeddings and store them in the vector database

if __name__ == '__main__':
    main()