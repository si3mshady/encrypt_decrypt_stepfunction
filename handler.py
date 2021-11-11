import uuid, json, random, boto3
from cryptography.fernet import Fernet
from datetime import datetime
from faker import Faker
fake = Faker()

def get_secret(secret_name):    
    if secret_name == "sqs_url":
        key = "sqs_url"    
    sm_ = boto3.client('secretsmanager', region_name='us-east-1')
    result = sm_.get_secret_value(SecretId=secret_name).get('SecretString')
    return json.loads(result)[key]

def encrypt_data(data,context):
    key = Fernet.generate_key()
    print(type(key))
    print(str(key))
    fernet = Fernet(key)
    encMessage = fernet.encrypt(data.encode())   
    return {"data":encMessage}
    

def get_random_outcome():
    return random.choice(["successful", "unsuccessful"]) 
    
def generate_fake_transaction(data,context):
    tx = {}
    tx['id'] = str(uuid.uuid4())
    tx["paymentBrand"] = fake.credit_card_provider()
    tx["amount"]  = fake.pricetag()
    tx["currency"] = "US"
    tx["result"] = {"code":str(uuid.uuid1()), \
     "status": get_random_outcome() }
    tx["card"] = {
        "last4Digits":fake.credit_card_number()[11:],
        "card_holder": fake.name(),
        "expiration_date": fake.credit_card_expire()
            }
    tx['timestamp'] = datetime.now().timestamp()

    if tx['result']['status'] == "unsuccessful":
        raise Exception("Transaction was unsuccessful")

    return str(json.dumps(tx, default=str))

def add_to_ddb_and_sqs(data,context):
    print(data)
    id = str(uuid.uuid4())
    ddb = boto3.client('dynamodb')
    sqs = boto3.client('sqs')   
    encrypted_transaction = {"data":{'S': data['data']}, "id": {'S': id  }}
    sqs_url = get_secret(secret_name="sqs_url")  
    kwargs = {"QueueUrl": sqs_url, "MessageBody": id } 
      
    ddb.put_item(TableName='test_table_2', Item=encrypted_transaction)
    sqs.send_message(**kwargs)
    
def decrypt_transaction(data,context):
    print(data)
