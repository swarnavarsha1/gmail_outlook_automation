<!--
Title: Customer Support Email Automation System | Langchain/Langgraph Integration
Description: Automate customer support emails with our system built using Langchain/Langgraph. Features include email categorization, query synthesis, draft email creation, and email verification.
Keywords: Customer support automation, email automation, Langchain, Langgraph, AI email agents, Gmail API, Python email automation, email categorization, email verification, AI agents, AI tools
-->

# Customer Support Email Automation with AI Agents and RAG

**A Langgraph system for streamlining client interactions, ensuring every customer receives a quick and accurate response. 🌟**

## Introduction

In today's fast-paced environment, customers demand quick, accurate, and personalized responses—expectations that can overwhelm traditional support teams. Managing large volumes of emails, categorizing them, crafting appropriate replies, and ensuring quality consumes significant time and resources, often leading to delays or errors, which can harm customer satisfaction.

**Customer Support Email Automation** is an AI solution designed to enhance customer communication for businesses. Leveraging a Langgraph-driven workflow, multiple AI agents collaborate to efficiently manage, categorize, and respond to customer emails. The system also implements RAG (Retrieval-Augmented Generation) technology to deliver accurate responses to any business or product-related questions.

## Features

### Email Inbox Management with AI Agents

- Continuously monitors the agency's Gmail and Outlook inbox
- Categorizes emails into 'customer complaint', 'product inquiry', 'customer feedback', 'samsara related' or 'unrelated'
- Automatically handles irrelevant emails to maintain efficiency
- **Manual Email Check Buttons**: Users can manually check for new emails using the **"Check Gmail"** and **"Check Outlook"** buttons on the frontend dashboard. These buttons trigger email fetching and draft generation for new messages.

### AI Response Generation

- Quickly drafts emails for customer complaints and feedback using Langgraph
- Utilizes RAG techniques to answer product/service-related questions accurately
- Creates personalized email content tailored to each customer's needs

### Samsara Integration for Fleet Management

- Extracts location, vehicle, and driver details from Samsara API
- Automatically identifies fleet-related inquiries and fetches relevant data
- Ensures accurate and up-to-date vehicle tracking and response generation for transport and logistics

### Quality Assurance with AI

- Automatically checks email quality, formatting, and relevance
- Ensures every response meets high standards before reaching the client

## Frontend Dashboard

The system includes a user-friendly **React.js frontend** that provides an intuitive interface for monitoring email activity. Key features include:

- **Email Statistics Overview**: Displays total received emails, read/unread count, replied emails, and drafted responses.
- **Email Accounts Panel**: Users can switch between connected email accounts (Gmail and Outlook) to monitor emails from different sources.
- **Recent Emails Section**: Lists the most recent emails received.
- **Search and Filter Options**: Users can search emails by sender and filter by time range.
- **Manual Email Checking**: The **"Check Gmail"** and **"Check Outlook"** buttons allow users to manually fetch new emails and trigger the AI draft generation process.

## How It Works

1. **Email Monitoring**: The system constantly checks for new emails in the agency's Gmail/Outlook inbox using the Gmail API/Outlook credentials.
2. **Email Categorization**: AI agents sort each email into predefined categories.
3. **Response Generation**: 
   - For complaints or feedback: The system quickly drafts a tailored email response.
   - For service/product questions: The system uses RAG to retrieve accurate information from agency documents and generates a response.
   - For Samsara-related emails: The system fetches the respective location, vehicle details, or driver details, ensuring accurate fleet tracking.
4. **Quality Assurance**: Each draft email undergoes AI quality and formatting checks.
5. **Sending**: Approved emails are sent to the client promptly, ensuring timely communication.

## System Flowchart

This is the detailed flow of the system:

[![](https://mermaid.ink/img/pako:eNqllEuP2jAQx7-KZa6AgAB5HFrxFlJBXbarIsIeTDwBi2CntrPAEr57TRIoW_Wwojk585_fvJLxCQeCAvZwGIl9sCFSox_9JUfm6fgTwZkWEo0mnfE3NOYrcXgtNFSpfEHd01jlZjTYxfr49Zyr3YuaTgWawt4ohEUqRQt_wCn6LkUASr3eOw5FYpQXTrjagwR6Q3p-j2hYC8neITcWXC_jXriEyDjQFHXv7b1EabEDiXpiF0eEcY1ME0MAuiLBNkV9_6dk2uidNXD9IaQpjyaBRgP-K2HymKKB_3zkegPqUsJTApKBQqEJN-uMCnKQzWLuj0CjTtYCCqXY3XnMM49_pu1n0tA3iUU4A0L_0odZWZ04luINUjTyn4HTD7PIPaamO4Vm8MYUE9z0mIujQjzonMkmlUtKHyMwHzJkUeSVQjcsKy3FFryS4zjFubJnVG-8RnwoByIS0ivVarV7vFvgq9Uf3LKsz-K9a_bV6hG8f80ePoQP_i_78DY69xF8VOBu-BA-v2Z_DF8UOKX08zguY7NW5j-i5sI4XcItsdmNHSyxZ46UyO0SL_nZ-JFEC7M5Afa0TKCMpUjWG-yFJFLmLYmp2ds-I2tJdjdrTDj2TviAvUbLrjYtt2G1XLdVr7XtZhkfjbnqNJyW4zZt17LdpuO0z2X8LoQJUau6rbbt2la7btmWW6s3s3iLTMxLAHq5zCb5dRcIHrI1Pv8GXQeX4g?type=png)](https://mermaid.live/edit#pako:eNqllEuP2jAQx7-KZa6AgAB5HFrxFlJBXbarIsIeTDwBi2CntrPAEr57TRIoW_Wwojk585_fvJLxCQeCAvZwGIl9sCFSox_9JUfm6fgTwZkWEo0mnfE3NOYrcXgtNFSpfEHd01jlZjTYxfr49Zyr3YuaTgWawt4ohEUqRQt_wCn6LkUASr3eOw5FYpQXTrjagwR6Q3p-j2hYC8neITcWXC_jXriEyDjQFHXv7b1EabEDiXpiF0eEcY1ME0MAuiLBNkV9_6dk2uidNXD9IaQpjyaBRgP-K2HymKKB_3zkegPqUsJTApKBQqEJN-uMCnKQzWLuj0CjTtYCCqXY3XnMM49_pu1n0tA3iUU4A0L_0odZWZ04luINUjTyn4HTD7PIPaamO4Vm8MYUE9z0mIujQjzonMkmlUtKHyMwHzJkUeSVQjcsKy3FFryS4zjFubJnVG-8RnwoByIS0ivVarV7vFvgq9Uf3LKsz-K9a_bV6hG8f80ePoQP_i_78DY69xF8VOBu-BA-v2Z_DF8UOKX08zguY7NW5j-i5sI4XcItsdmNHSyxZ46UyO0SL_nZ-JFEC7M5Afa0TKCMpUjWG-yFJFLmLYmp2ds-I2tJdjdrTDj2TviAvUbLrjYtt2G1XLdVr7XtZhkfjbnqNJyW4zZt17LdpuO0z2X8LoQJUau6rbbt2la7btmWW6s3s3iLTMxLAHq5zCb5dRcIHrI1Pv8GXQeX4g)

## Tech Stack

* Langchain & Langgraph: for developing AI agents workflow.
* Langserve: simplify API development & deployment (using FastAPI).
* Gemini APIs: for LLMs access.
* Google Gmail API
* Samsara API: for fleet and vehicle data integration

## How to Run

### Prerequisites

- Python 3.8+
- Node.js 16+
- Google Gemini API key (for embeddings)
- Gmail API credentials
- Outlook API setup
- Samsara API credentials
- Necessary Python libraries (listed in `requirements.txt`)

### Setup

1. **Clone the repository:**

   ```sh
   git clone https://github.com/swarnavarsha1/gmail_outlook_automation.git
   cd gmail_outlook_automation
   ```

2. **Create and activate a virtual environment:**

   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Backend setup:**

Navigate to the backend directory
   ```sh
   cd backend-email-automation
   ```
Install dependencies
   ```sh
   pip install -r requirements.txt
   ```
Start the backend server
   ```sh
   python deploy_api.py
   ```

4. **Frontend setup:**

Navigate to the frontend directory
   ```sh
   cd frontend-email-automation
   ```
Install dependencies
   ```sh
   npm install
   ```
Start the frontend server
   ```sh
   npm run dev
   ```

### Customization

You can customize the behavior of each agent by modifying the corresponding methods in the `Nodes` class or the agents' prompt `prompts` located in the `src` directory.

You can also add your own agency data into the `data` folder, then you must create your own vector store by running (update first the data path):

```sh
python create_index.py
```
### Generating Draft Emails

You can generate draft emails from the frontend using "Check Gmail" and "Check Outlook" buttons. Alternatively, you can generate drafts from the backend using the following commands:
```sh
cd backend-email-automation
python main.py --service gmail
python main.py --service outlook
```