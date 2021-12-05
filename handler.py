import uuid, json, random, boto3
from cryptography.fernet import Fernet
from datetime import datetime
from faker import Faker
fake = Faker()

TABLE_NAME = 'transactions'
KEY_NAME = 'symmetric.key'
BUCKET_NAME = 'symmetric-key-si3mshady'

def get_encryption_key():
    s3 = boto3.client('s3')
    s3_response = s3.get_object(Bucket=BUCKET_NAME, Key=KEY_NAME)
    encryption_key = s3_response['Body'].read()
    print(encryption_key)
    return encryption_key



def get_secret(secret_name):    
    if secret_name == "sqs_url":
        key = "sqs_url"    
    sm_ = boto3.client('secretsmanager', region_name='us-east-1')
    result = sm_.get_secret_value(SecretId=secret_name).get('SecretString')
    return json.loads(result)[key]

def encrypt_data(data,context):
 
    fernet = Fernet(get_encryption_key())
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
    r = ddb.put_item(TableName=TABLE_NAME, Item=encrypted_transaction)
    sqs.send_message(**kwargs)
    return sqs_url 
  

def get_id_from_sqs(sqs_url):
    sqs = boto3.client('sqs')  
    kwargs = {"QueueUrl": sqs_url,"MaxNumberOfMessages":1,
    "VisibilityTimeout":5 } 
    response = sqs.receive_message(**kwargs)    
    return response.get('Messages')[0]['Body']

def get_from_ddb(message_id):
    ddb = boto3.resource('dynamodb')
    table = ddb.Table(TABLE_NAME)
    try:
        response = table.get_item(
            TableName=TABLE_NAME,
            Key={
                'id': message_id
                }
        
        )
       
        return response
    except Exception as e:
        print(e)

    
def decrypt_transaction(data,context):
    
    message_id = get_id_from_sqs(data)
    data=get_from_ddb(message_id).get('Item').get('data')
    fernet = Fernet(get_encryption_key())
    decrypted_message = fernet.decrypt(data.encode())   
    decrypted_message_decoded = decrypted_message.decode()
    return decrypted_message_decoded
    
 


#Elliott Arnold - stepfunction workflow - encrypt/ decrypt payment information 
#12-5-21 part 2 
