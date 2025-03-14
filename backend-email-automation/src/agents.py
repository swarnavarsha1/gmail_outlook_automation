from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .structure_outputs import *
from .prompts import *
from config import config_manager
import os
import re

class Agents():
    def __init__(self):
        # Get configuration
        config = config_manager.get_config()
        api_key = config.ai.gemini_api_key

        # Initialize Gemini with API key
        gemini = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash", 
            temperature=0.1,
            google_api_key=api_key
        )
        
        # QA assistant chat with API key
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=api_key
        )
        vectorstore = Chroma(persist_directory="db", embedding_function=embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        # Load custom prompts from text file, if available
        custom_prompts = self._load_custom_prompts()
        
        # Use either custom prompts or default prompts
        categorize_email_prompt_text = custom_prompts.get('CATEGORIZE_EMAIL_PROMPT', CATEGORIZE_EMAIL_PROMPT)
        generate_rag_queries_prompt_text = custom_prompts.get('GENERATE_RAG_QUERIES_PROMPT', GENERATE_RAG_QUERIES_PROMPT)
        generate_rag_answer_prompt_text = custom_prompts.get('GENERATE_RAG_ANSWER_PROMPT', GENERATE_RAG_ANSWER_PROMPT)
        email_writer_prompt_text = custom_prompts.get('EMAIL_WRITER_PROMPT', EMAIL_WRITER_PROMPT)
        email_proofreader_prompt_text = custom_prompts.get('EMAIL_PROOFREADER_PROMPT', EMAIL_PROOFREADER_PROMPT)
        identify_samsara_query_prompt_text = custom_prompts.get('IDENTIFY_SAMSARA_QUERY_PROMPT', IDENTIFY_SAMSARA_QUERY_PROMPT)
        generate_samsara_response_prompt_text = custom_prompts.get('GENERATE_SAMSARA_RESPONSE_PROMPT', GENERATE_SAMSARA_RESPONSE_PROMPT)

        # The rest of your agent initialization code using the prompt texts
        email_category_prompt = PromptTemplate(
            template=categorize_email_prompt_text, 
            input_variables=["email"]
        )
        self.categorize_email = (
            email_category_prompt | 
            gemini.with_structured_output(CategorizeEmailOutput)
        )

        generate_query_prompt = PromptTemplate(
            template=generate_rag_queries_prompt_text, 
            input_variables=["email"]
        )
        self.design_rag_queries = (
            generate_query_prompt | 
            gemini.with_structured_output(RAGQueriesOutput)
        )
        
        qa_prompt = ChatPromptTemplate.from_template(generate_rag_answer_prompt_text)
        self.generate_rag_answer = (
            {"context": retriever, "question": RunnablePassthrough()}
            | qa_prompt
            | gemini
            | StrOutputParser()
        )

        writer_prompt = ChatPromptTemplate.from_messages([
            ("system", email_writer_prompt_text),
            MessagesPlaceholder("history"),
            ("human", "{email_information}")
        ])
        self.email_writer = (
            writer_prompt | 
            gemini.with_structured_output(WriterOutput)
        )

        proofreader_prompt = PromptTemplate(
            template=email_proofreader_prompt_text, 
            input_variables=["initial_email", "generated_email"]
        )
        self.email_proofreader = (
            proofreader_prompt | 
            gemini.with_structured_output(ProofReaderOutput) 
        )

        samsara_query_prompt = PromptTemplate(
            template=identify_samsara_query_prompt_text, 
            input_variables=["email"]
        )
        self.identify_samsara_query = (
            samsara_query_prompt | 
            gemini.with_structured_output(SamsaraQueryOutput)
        )
        
        samsara_response_prompt = PromptTemplate(
            template=generate_samsara_response_prompt_text,
            input_variables=["original_query", "query_type", "samsara_data"]
        )
        self.generate_samsara_response = (
            samsara_response_prompt | 
            gemini | 
            StrOutputParser()
        )
        
    def _load_custom_prompts(self):
        """
        Load custom prompts from text file.
        The file should have sections for each prompt, with format:
        
        # PROMPT_NAME
        prompt content...
        prompt content...
        
        # NEXT_PROMPT_NAME
        next prompt content...
        """
        custom_prompts = {}
        custom_prompts_path = "prompts/custom_prompts.py"
        
        if not os.path.exists(custom_prompts_path):
            print("No custom prompts file found. Using defaults.")
            return custom_prompts
            
        try:
            with open(custom_prompts_path, 'r') as file:
                content = file.read()
                
            # Split by sections (starting with # PROMPT_NAME)
            sections = re.split(r'#\s+([A-Z_]+)', content)[1:]  # Skip first empty section
            
            # Process sections in pairs (name, content)
            for i in range(0, len(sections), 2):
                if i + 1 < len(sections):
                    prompt_name = sections[i].strip()
                    prompt_content = sections[i + 1].strip()
                    custom_prompts[prompt_name] = prompt_content
            
            print(f"Loaded {len(custom_prompts)} custom prompts")
            return custom_prompts
            
        except Exception as e:
            print(f"Error loading custom prompts: {e}")
            return {}