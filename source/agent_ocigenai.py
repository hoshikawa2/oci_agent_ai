import sqlite3
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_community.chat_models.oci_generative_ai import ChatOCIGenAI
import requests
from requests.auth import HTTPBasicAuth

user_name = "YOUR_USER_NAME"
password = "YOUR_PASSWORD"

#--------------------------------------------------------------------------
# DB PERSISTENCE

# Create the connection with a database: SQLite
def connect_db():
    return sqlite3.connect('orders.db')

# Create the table orders if not exists
def create_orders_table():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT
        )
    """)
    conn.commit()
    conn.close()

# Add items to an order
def insert_item_to_db(item):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (item) VALUES (?)", (item,))
    conn.commit()
    conn.close()

# Delete item from an order
def delete_item_from_db(item):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE item = ?", (item,))
    conn.commit()
    conn.close()

# Search for items in order
def get_all_items_from_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT item FROM orders")
    items = cursor.fetchall()
    conn.close()
    return [item[0] for item in items]

#--------------------------------------------------------------------------
# REST SERVICES

def get_rest_service_auth(url):
    response = requests.get(url, auth=HTTPBasicAuth(user_name, password))
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Service request error. Status code: {response.status_code}")
        return None

def get_rest_service(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Service request error. Status code: {response.status_code}")
        return None

def post_request(url, data, headers=None):
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        return None

#--------------------------------------------------------------------------
# BUSINESS SERVICES

@tool
def insert_order(item):
    """Create an order with items."""
    insert_item_to_db(item)
    print("Item(s):", item)
    return {"message": "Items added to order"}

@tool
def delete_order(item):
    """Delete an Item in the order."""
    delete_item_from_db(item)
    print("Trying to remove:", item)
    return {"message": "Item excluded to order"}

@tool
def search_order():
    """Search an order with items."""
    print("Item(s):", get_all_items_from_db())
    return {"message": "That's it!"}

@tool
def order_cost():
    """This service gives the total of the order."""
    order_list = get_all_items_from_db()
    if not order_list:
        return {"message": "No items in the order"}

    total = len(order_list) * 10  # Supondo que cada item custa 10
    print("Total: $", total)
    return {"message": total}

@tool
def delivery_address(postalCode: str, number: str = "", complement: str = "") -> str:
    """Find the complete address of a postal code."""
    full_address = f"Paulista Avenue, 1000 - 01310-000 - Sao Paulo - SP"
    print(full_address)
    return str(full_address)

# @tool
# def delivery_address(postalCode: str, number: str = "", complement: str = "") -> str:
#     """Find the complete address of a postal code to delivery, along with the building number and complement.
#     The customer can ask for 'delivery to' or 'my address is'. postalCode normally is the postal code or CEP,
#     number is the number of buiding and complenent is the apartment or other complement for the address. always confirm the address
#     and the total cost of order."""
#
#     url = f"https://xxxxxxxxxxxxxxxxxxxxx.apigateway.us-ashburn-1.oci.customer-oci.com/cep/cep?cep={postalCode}"
#     response = get_rest_service_auth(url)
#
#     address = response["frase"]
#     full_address = f"{address}, Number: {number}, Complement: {complement}"
#     print(full_address)
#     return str(full_address)

#--------------------------------------------------------------------------
tools = [insert_order, order_cost, search_order, delivery_address, delete_order]

# PROMPT AND CONTEXT

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """You are an assistant that helps customers place orders at a restaurant.
        The customer can add an item into the order using 'insert_order' service. The item is understood as a request input by the customer
        Every time an item is added using 'insert_order', immediately call 'order_cost' to show the total. 
        Every time the customer ask for delivery or give the postal code (ZIP), always use the 'delivery_address' service to search for the postal code and 
        give the complete address.
        Every time the customer ask to check or view their order details, always call the 'search_order' service.
        Every time the customer ask to check their order price (cost order) like 'how much is it?' or 'what is the cost?', always call the 'order_cost' service.
        Every time the customer ask to delete an item, always call the 'delete_item' service.
        """),
        ("placeholder", "{messages}"),
    ]
)

#--------------------------------------------------------------------------
# OCI Generative AI DEFINITIONS

llm = ChatOCIGenAI(
    model_id="cohere.command-r-08-2024",
    service_endpoint="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
    compartment_id="ocid1.compartment.oc1..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    auth_profile="DEFAULT",  # replace with your profile name,
    model_kwargs={"temperature": 0.1, "top_p": 0.75, "max_tokens": 2000}
)

memory = MemorySaver()
langgraph_agent_executor = create_react_agent(
    model=llm, tools=tools, prompt=prompt, checkpointer=memory
)

config = {"configurable": {"thread_id": "test-thread"}}

#--------------------------------------------------------------------------
# CHAT

print("READY")
create_orders_table()  # Create the orders table

while (True):
    try:
        query = input()
        if query == "quit":
            break
        if query == "":
            continue
        messages = langgraph_agent_executor.invoke(
            {"messages": [("human", query)]}, config
        )["messages"]
        response = messages[-1].content
        print(response)
    except Exception as ex:
        None