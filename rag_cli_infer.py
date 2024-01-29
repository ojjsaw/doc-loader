import argparse
import json
import logging
import sys
import warnings
import os
from pprint import pprint
from langchain_community.embeddings import HuggingFaceEmbeddings
from transformers import AutoModel
from langchain_community.vectorstores.chroma import Chroma
from transformers import AutoTokenizer, pipeline
from optimum.intel.openvino import OVModelForCausalLM
from langchain.llms.huggingface_pipeline import HuggingFacePipeline
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQA

template = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
Use three sentences maximum and keep the answer as concise as possible.
Always say "thanks for asking!" at the end of the answer.

{context}

Question: {question}

Helpful Answer:"""
custom_rag_prompt = PromptTemplate.from_template(template)

def load_embeddings(embeddings_model):
    # trust_remote_code error workaround
    model = AutoModel.from_pretrained(embeddings_model, trust_remote_code=True)
    ############ TODO: Experiment Other embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name = embeddings_model,
        model_kwargs = {'device':'cpu'},
        encode_kwargs = {'normalize_embeddings': True}
    )
    return embeddings

def load_vector_retriever(storedir, embeddings):
    vector_store = Chroma(persist_directory=storedir, embedding_function=embeddings)
    ############ TODO: Experiment with retriever configs
    retriever = vector_store.as_retriever()
    #retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 6})
    return retriever, vector_store

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)
   
def main():
    logging.basicConfig(format='%(asctime)s | %(levelname)s: %(message)s', level=logging.INFO)
    warnings.filterwarnings("ignore")

    parser = argparse.ArgumentParser(description='Process a directory of HTML files recursively utilizing max cores in parallel.')
    parser.add_argument('--storedir', default='./VectorStores/20240128_222407', type=str, help='Path to the directory containing HTML files (default: 2023.3)')
    parser.add_argument('--modelid', default='Intel/neural-chat-7b-v3-3', type=str, help='LLM model (default: Intel/neural-chat-7b-v3-3)')
    parser.add_argument('--maxtokens', default=140, type=int, help='LLM model (default: 140)')

    # helenai/gpt2-ov
    args = parser.parse_args()

    config_file = args.storedir + "/process_docs_config.json"
    config_dict = {}
    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            config_dict = json.load(file)
    else:
        logging.error(f"Config file not found: {config_file}")
        sys.exit(1)

    for arg in vars(args):
        logging.info(f"{arg}: {getattr(args, arg)}")

    logging.info(f"Configs found in: {config_file}")
    pprint(config_dict)

    embeddings = load_embeddings(config_dict['emodel'])
    retriever, _ = load_vector_retriever(args.storedir, embeddings)

    tokenizer = AutoTokenizer.from_pretrained(args.modelid)
    model = OVModelForCausalLM.from_pretrained(
        model_id=args.modelid, 
        device='CPU', 
        ov_config={"PERFORMANCE_HINT": "LATENCY"},
        trust_remote_code=True,
        #load_in_8bit=True
        )
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=args.maxtokens)
    llm = HuggingFacePipeline(pipeline=pipe)

    # qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)
    # qa_chain.invoke("")

    rag_chain_from_docs = (
        RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
        | custom_rag_prompt
        | llm
        | StrOutputParser()
    )
    rag_chain_with_source = RunnableParallel(
        {"context": retriever, "question": RunnablePassthrough()}
    ).assign(answer=rag_chain_from_docs)
    
    #result = rag_chain_with_source.invoke("what is openvino")
    output = {}
    curr_key = None
    for chunk in rag_chain_with_source.stream("what is openvino"):
        for key in chunk:
            if key not in output:
                output[key] = chunk[key]
            else:
                output[key] += chunk[key]
            if key != curr_key:
                print(f"\n\n{key}: {chunk[key]}", end="", flush=True)
            else:
                print(chunk[key], end="", flush=True)
            curr_key = key


if __name__ == '__main__':
    main()