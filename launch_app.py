import requests, os, uuid, urllib.request, shutil, hashlib, json
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

UPLOAD_DIR = './uploads'
ACCESS_RIGHTS = 0o755

the_api = Flask(__name__)
the_api.config['UPLOAD_FOLDER'] = UPLOAD_DIR

them_files_list = [
    {
        "file_name": "sample",
        "id": "sample",
        "checksum": "sample"
    }
]

with open('config.json') as config_file:
    config = json.load(config_file)

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def delete_from_them_files_list(that_file):
    for the_file in them_files_list:
        if the_file['id'] == that_file['id']:
            them_files_list.remove(the_file)

def update_them_files_list(filename, checksum):
    newID = str(uuid.uuid1())
    them_files_list.append({"file_name": filename, "id": newID, "checksum": checksum})
    
    return newID

def generate_checksum(filename):
    with open('./uploads/'+filename, "rb") as f:
        bytes = f.read()
        readable_hash = hashlib.md5(bytes).hexdigest()
        
        return str(readable_hash)

def check_checksum(the_file):
    before_retrieval = generate_checksum(the_file['file_name'])
    if before_retrieval == the_file['checksum']:
        return True
    else:
        return False

def create_them_nodes(filename):
    node_count = list(config.values())[1]
    node_count_now = len([i for i in os.listdir(UPLOAD_DIR) if os.path.isdir(i)])
    file_size = os.stat('./uploads/'+filename).st_size
    chunk_size = list(config.values())[2]
    chunks = file_size//chunk_size
  
    if node_count_now == 0:
        for i in range(1, min(chunks+1, node_count+1)):
            os.makedirs("./uploads/node_{}".format(i), ACCESS_RIGHTS)
        if chunks == 0:
            os.makedirs("./uploads/node_{}".format(1), ACCESS_RIGHTS)
    
    print(chunks, node_count_now)
    if chunks > node_count_now:
        for i in range(1, min(chunks+1, node_count+1)):
            os.makedirs("./uploads/node_{}".format(i), ACCESS_RIGHTS)

def load_balance_them_files(filename):
    create_them_nodes(filename)

@the_api.route('/files/list', methods=['GET'])
def them_list_of_files():
    return jsonify(them_files_list) if len(them_files_list) > 1 else jsonify([])

@the_api.route('/files/<file_id>', methods=['GET'])
def download_them_files(file_id):
    print(file_id)
    filename = ""
    for the_file in them_files_list:
        if the_file['id'] == file_id:
            that_file = the_file
            filename = the_file['file_name']
            break

    if not os.path.isfile('./uploads/'+filename):
        return "requested object {} is not found".format(file_id), 404

    if filename is not "":
        if check_checksum(that_file):
            return send_file("./uploads/"+filename, as_attachment=True), 200
        else:
            return jsonify("one or more chunks are missing"), 500
    else:
        return "requested object {} is not found".format(file_id), 404

@the_api.route('/files/<file_id>', methods=['DELETE'])
def delete_them_files(file_id):
    # file_id = file_id[7:43]
    filename = ""
    for the_file in them_files_list:
        if the_file['id'] == file_id:
            that_file = the_file
            filename = the_file['file_name']
            break

    if not os.path.isfile('./uploads/'+filename):
        return jsonify("Requested object {} is not found".format(file_id)), 404

    if filename is not "":
        print(filename)
        os.remove("./uploads/"+filename)
        delete_from_them_files_list(that_file)
        return jsonify("object {} deleted successfully".format(file_id)), 200
    else:
        return jsonify("Requested object {} is not found".format(file_id)), 404

@the_api.route('/files', methods=['PUT'])
def upload_them_files():
    if 'file' not in request.files:
        resp = jsonify({'message' : 'No file part in the request'})
        resp.status_code = 400
        return resp
    file = request.files['file']
    if file.filename == '':
        resp = jsonify({'message' : 'No file selected for uploading'})
        resp.status_code = 400
        return resp

    if os.path.isfile('./uploads/'+secure_filename(file.filename)):
        return jsonify("File Already Exists"), 409
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(the_api.config['UPLOAD_FOLDER'], filename))
        checksum = generate_checksum(filename)
        newID = update_them_files_list(filename, checksum)
        resp = jsonify(
            {
                'message' : 'File successfully uploaded',
                'id': newID,
                'checksum': checksum
            }
        )
        resp.status_code = 200

        load_balance_them_files(filename)

        return str(newID), 200

def main():
    if os.path.exists(UPLOAD_DIR):
        shutil.rmtree(UPLOAD_DIR)
    os.makedirs(UPLOAD_DIR, ACCESS_RIGHTS)


    the_api.run(debug=True)

if __name__ == '__main__':
    main()