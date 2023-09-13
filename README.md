### System Dependencies
- Python 3.8+
### Setup
- Navigate to the directory containing app.py
- Create a virtual environment using
```
python3 -m venv venv
```
- Activate the virtual environment using
```
source venv/bin/activate
```
- Install requirements using
```
pip install -r requirements.txt
```
- Run the server using
```
flask run
```
- The server will be live on `http://127.0.0.1:5000/`
​
### API Working
#### Request
Endpoint: /keyword?keyword=car
Method: GET (Replace car with the keyword of your choice)
Response:
```
{
    "predictions": [{
        "filename": "abc",
        "label": "object",
        "probability": 50
    }]
}
```
​
​
Endpoint: /file
Method: POST (Send/Upload image using form-data with the keyname 'image')
Request:
```
{
    "image": file
}
````
​
Response:
```
{
    "predictions": [{
        "filename": "abc",
        "label": "object",
        "probability": 50
    }]
}
```
​
