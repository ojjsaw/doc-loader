import os
import time
from dotenv import load_dotenv

from langchain.llms import HuggingFacePipeline
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA

from transformers import AutoTokenizer, pipeline
from optimum.intel.openvino import OVModelForCausalLM

load_dotenv(verbose=True)
cache_dir         = os.environ['CACHE_DIR']
model_vendor      = os.environ['MODEL_VENDOR']
model_name        = os.environ['MODEL_NAME']
model_precision   = os.environ['MODEL_PRECISION']
inference_device  = os.environ['INFERENCE_DEVICE']
document_dir      = os.environ['DOCUMENT_DIR']
vectorstore_dir   = os.environ['VECTOR_DB_DIR']
vector_db_postfix = os.environ['VECTOR_DB_POSTFIX']
num_max_tokens    = int(os.environ['NUM_MAX_TOKENS'])
embeddings_model  = os.environ['MODEL_EMBEDDINGS']
rag_chain_type    = os.environ['RAG_CHAIN_TYPE']
ov_config         = {"PERFORMANCE_HINT":"LATENCY", "NUM_STREAMS":"1", "CACHE_DIR":cache_dir}

### WORKAROUND for "trust_remote_code=True is required error" in HuggingFaceEmbeddings()
from transformers import AutoModel
model = AutoModel.from_pretrained(embeddings_model, trust_remote_code=True) 

embeddings = HuggingFaceEmbeddings(
    model_name = embeddings_model,
    model_kwargs = {'device':'cpu'},
    encode_kwargs = {'normalize_embeddings':True}
)

vectorstore_dir = f'{vectorstore_dir}{vector_db_postfix}'
vectorstore = Chroma(persist_directory=vectorstore_dir, embedding_function=embeddings)
retriever = vectorstore.as_retriever()
#    search_type='similarity_score_threshold', 
#    search_kwargs={
#        'score_threshold' : 0.8, 
#        'k' : 4
#    }
#)
print(f'** Vector store : {vectorstore_dir}')

model_id = f'{model_vendor}/{model_name}'
tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=cache_dir)
ov_model_path = f'./{model_name}/{model_precision}'
model = OVModelForCausalLM.from_pretrained(model_id=ov_model_path, device=inference_device, ov_config=ov_config, cache_dir=cache_dir)
pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=num_max_tokens)
llm = HuggingFacePipeline(pipeline=pipe)
qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type=rag_chain_type, retriever=retriever)


def run_generation(text_user_en):
    ans = qa_chain.run(text_user_en)
    return ans

# CLI interface
def main():
    print("Welcome to the Interactive OpenVINO-RAG Chatbot")
    try:
        while True:
            user_input = input("Enter your question (or type 'exit' to quit): ").strip()
            if user_input.lower() == 'exit':
                break
            
            if user_input:
                stime = time.time()
                ans = run_generation(user_input)
                etime = time.time()

                wc = len(ans.split())  # simple word count
                process_time = etime - stime
                words_per_sec = wc / process_time

                print(f"Response: {ans}\nWord count: {wc}, Processing Time: {process_time:.1f} sec, {words_per_sec:.2f} words/sec\n")
            else:
                print("Please enter a question.")
    except KeyboardInterrupt:
        print("\nExiting the chatbot...")

if __name__ == "__main__":
    main()