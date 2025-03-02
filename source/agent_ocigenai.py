# Adapter for OCI Generative AI Agent

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import BaseTool, StructuredTool, Tool, tool
from langchain_community.chat_models.oci_generative_ai import ChatOCIGenAI
import requests
from requests.auth import HTTPBasicAuth

user_name = "#######################"
password = "#######################"

order_list = []  # Peristence for Order

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
def insert_order(items):
    """Create an order with items. The customer can ask for items of a restaurant. The customer want to include an item."""
    global order_list
    order_list.extend(items)  # Adiciona os novos itens ao pedido
    print("Item(s) incluído(s):", items)
    return {"message": "Items added to order", "current_order": order_list}

@tool
def delete_order(item):
    """Delete an Item in the order. The customer can regret about one or more items.
    The customer can ask for delete item of a restaurant.
    The customer can request to 'Remove the item' or 'I don't want anymore the item' or 'Delete the item'."""
    global order_list
    print("Trying to remove:", item)
    for global_item in order_list:
        if global_item in item:
            order_list.remove(global_item)
            print("Item(s) excluído(s):", global_item)
    return {"message": "Item excluded to order", "current_order": order_list}

@tool
def search_order():
    """Search an order with items."""
    global order_list
    print("Item(s) incluído(s):", order_list)
    return {"message": "Items added to order", "current_order": order_list}

@tool
def order_cost():
    """This service gives the total of the order, summarizing the items.
    If the customer says 'give me the bill' or 'summarize the order' or 'what is the total' or 'how much is it'."""
    global order_list
    if not order_list:
        return {"message": "No items in the order"}

    total = len(order_list) * 10  # Supondo que cada item custa 10
    print("Total: $", total)
    return {"total_cost": total, "order_items": order_list}

# @tool
# def delivery_address(postalCode: str, number: str = "", complement: str = "") -> str:
#     """Find the complete address of a postal code to delivery, along with the building number and complement.
#     The customer can ask for 'delivery to' or 'my address is'. postalCode normally is the postal code or CEP,
#     number is the number of buiding and complenent is the apartment or other complement for the address. always confirm the address
#     and the total cost of order."""
#
#     url = f"https://cihjkhlijtmunsiiokgrhetowu.apigateway.us-ashburn-1.oci.customer-oci.com/cep/cep?cep={postalCode}"
#     response = get_rest_service_auth(url)
#
#     address = response["frase"]
#     full_address = f"{address}, Number: {number}, Complement: {complement}"
#     print(full_address)
#     return str(full_address)


@tool
def delivery_address(postalCode: str, number: str = "", complement: str = "") -> str:
    """Find the complete address of a postal code to delivery, along with the building number and complement.
    The customer can ask for 'delivery to' or 'my address is'. postalCode normally is the postal code or CEP,
    number is the number of buiding and complenent is the apartment or other complement for the address. always confirm the address
    and the total cost of order."""

    full_address = f"Avenida Paulista, 1000 - 01310-000 - São Paulo - SP"
    print(full_address)
    return str(full_address)

#--------------------------------------------------------------------------

tools = [insert_order, order_cost, search_order, delivery_address, delete_order]


# PROMPT AND CONTEXT

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """Você é um assistente que ajuda clientes a fazer pedidos em um restaurante. 
        Depois que o cliente adiciona um item ao pedido, sempre informe o total. 
        Se o cliente fornecer um código postal (ou CEP), use a ferramenta find_address para obter o endereço completo. 
        O cliente pode consultar a qualquer momento os items pedidos. o cliente pode solicitar a entrega no endereco 
        dizendo 'me entregue no endereco ou no cep', 'meu endereço é e digitar o codigo postal ou cep ou rua'"""),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

#--------------------------------------------------------------------------
# OCI Generative AI DEFINITIONS

llm = ChatOCIGenAI(
    model_id="cohere.command-r-08-2024",
    service_endpoint="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
    compartment_id="ocid1.compartment.oc1..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    auth_profile="LATINOAMERICA",  # replace with your profile name,
    model_kwargs={"temperature": 0.1, "top_p": 0.75, "max_tokens": 2000}
)

agent = create_tool_calling_agent(llm, tools, prompt)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

#--------------------------------------------------------------------------
# CHAT

print("READY")

while (True):
    try:
        query = input()
        if query == "quit":
            break
        response = agent_executor.invoke({
            "input": query
        }
        )
        print(response)
    except:
        print("Invalid Command")

