import oci
import os

# Determina o diretório raiz do projeto (onde está o key.pem)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
KEY_PATH = os.path.join(BASE_DIR, "key.pem")

# Configurações do OCI
config = {
    "user": "ocid1.user.oc1..aaaaaaaavppmy2njmvirerpaa77hdkb5ezxshuio242l7mij6f2cy6k5tqba",
    "key_file": KEY_PATH,
    "fingerprint": "5f:a9:ba:d2:74:56:4b:9e:69:97:f5:80:f9:62:9b:5c",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaa6rxukxgoxpzwgeunjqsr3dm7m6azjauirt5xlqzjkru7yf2gzowq",
    "region": "sa-saopaulo-1"
}

OCI_BUCKET_NAME = "bucket-trabalho"

def get_object_storage_client():
    if not os.path.exists(KEY_PATH):
        raise FileNotFoundError(f"Arquivo de chave OCI nao encontrado em: {KEY_PATH}")
    return oci.object_storage.ObjectStorageClient(config)

def upload_to_oci(file_data, object_name):

    """
    Faz upload de um arquivo para o Bucket da Oracle Cloud.
    :param file_data: Pode ser um caminho de arquivo (string) ou um objeto de arquivo (file-like).
    :param object_name: O nome que o objeto terá no bucket.
    """
    client = get_object_storage_client()
    try:
        # Obter o namespace do tenancy
        namespace = client.get_namespace().data
        
        if isinstance(file_data, str):
            # Se for um caminho de arquivo
            if not os.path.exists(file_data):
                print(f"Erro: Arquivo {file_data} não encontrado.")
                return None
            with open(file_data, 'rb') as f:
                client.put_object(
                    namespace,
                    OCI_BUCKET_NAME,
                    object_name,
                    f
                )
        else:
            # Se for um objeto de arquivo (ex: request.files['file'])
            # Certifica-se de que o ponteiro está no início
            if hasattr(file_data, 'seek'):
                file_data.seek(0)
                
            client.put_object(
                namespace,
                OCI_BUCKET_NAME,
                object_name,
                file_data
            )
        
        # Gera a URL do objeto
        url = f"https://objectstorage.{config['region']}.oraclecloud.com/n/{namespace}/b/{OCI_BUCKET_NAME}/o/{object_name}"
        return url
    except Exception as e:
        print(f"Erro ao fazer upload para OCI: {e}")
        return None
