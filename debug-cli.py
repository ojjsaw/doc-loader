import argparse
import json
import logging
import sys
import time
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
from chromadb.config import Settings

template = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
Use three sentences maximum and keep the answer as concise as possible.
Always say "thanks for asking!" at the end of the answer.

{context}

Question: {question}

Helpful Answer:"""
custom_rag_prompt = PromptTemplate.from_template(template)

def load_embeddings(embeddings_model):

    return embeddings

def main():
    logging.basicConfig(format='%(asctime)s | %(levelname)s: %(message)s', level=logging.INFO)
    warnings.filterwarnings("ignore")

    parser = argparse.ArgumentParser(description='Use rag lanchain in cli mode.')
    parser.add_argument('--storedir', default='/root/ojas-workdir/ov-llm-rag/openvino-llm-chatbot-rag/.vectorstore_1000_100', type=str, help='Path to the vectorstore dir (default: /root/ojas-workdir/ov-llm-rag/openvino-llm-chatbot-rag/.vectorstore_1000_100)')
    parser.add_argument('--modelid', default='/root/ojas-workdir/doc-loader/INT4', type=str, help='LLM model (default: /root/ojas-workdir/doc-loader/ov_model)')
    parser.add_argument('--maxtokens', default=140, type=int, help='LLM model (default: 140)')

    args = parser.parse_args()

    for arg in vars(args):
        logging.info(f"{arg}: {getattr(args, arg)}")

    embeddings_model = 'jinaai/jina-embeddings-v2-base-en'
    # trust_remote_code error workaround
    model = AutoModel.from_pretrained(embeddings_model, trust_remote_code=True)
    ############ TODO: Experiment Other embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name = embeddings_model,
        model_kwargs = {'device':'cpu'},
        encode_kwargs = {'normalize_embeddings': True}
    )
    vector_store = Chroma(persist_directory=args.storedir, embedding_function=embeddings)
    retriever = vector_store.as_retriever()
    #retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 6})

    tokenizer = AutoTokenizer.from_pretrained('Intel/neural-chat-7b-v3-1')
    model = OVModelForCausalLM.from_pretrained(
        model_id=args.modelid, 
        device='CPU', 
        ov_config={"PERFORMANCE_HINT": "LATENCY"}
        )
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=args.maxtokens)
    llm = HuggingFacePipeline(pipeline=pipe)
    qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)

    while True:
        question = input("Enter your question (or 'exit' to quit): ")
        if question.lower() == 'exit':
            print("Exiting...")
            break

        start_time = time.time()
        result = qa_chain.run(question)
        end_time = time.time()
        duration = end_time - start_time

        output = f'{result} \nDuration: {duration:.2f} sec | Model: {args.modelid}'
        print(output)

if __name__ == '__main__':
    main()