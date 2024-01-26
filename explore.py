import glob
from pprint import pprint
import bs4
from langchain_community.document_loaders import ReadTheDocsLoader
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents.base import Document
from tqdm import tqdm

document_dir="2023.3"

def generate_documents_from_html(glob_pattern:str, max_doc_count:int=-1) -> list[Document]:
    doc_count = 0

    html_files = glob.glob(glob_pattern, recursive=True)
    print(len(html_files))

    documents = []
    for html_file in tqdm(html_files):
        #print(f'*** {html_file}')
        with open(html_file, 'rt', encoding='utf-8') as f:
            html_contents = ''.join(f.readlines())

        soup = bs4.BeautifulSoup(html_contents, 'html.parser')
        #for script in soup(['script', 'style']):       # Remove unnecessary tags
        #    script.decompose()

        # Extract text from 'main' tag
        main_section = soup.find('main')
        if main_section is not None:
            text = main_section.get_text()
            #lines = (line.strip() for line in text.splitlines())
            #result = '\n'.join(line for line in lines if line)
            text = ''.join([line+'\n' for line in text.splitlines() if line != '']) # Remove empty lines
            doc = Document(page_content=text, metadata={'source':html_file})
            #print(doc.page_content) 
            with open("testhiscode.txt", 'w', encoding='utf-8') as file:
                file.write(text)
            documents.append(doc)

            doc_count += 1
            if max_doc_count != -1 and doc_count >= max_doc_count:
                break

    return documents

#WebBaseLoader_test(document_dir)
generate_documents_from_html(f'{document_dir}/**/*.html')