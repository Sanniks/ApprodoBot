FROM python:3.12
WORKDIR /ApprodoBot_dev
COPY requirements.txt /ApprodoBot_dev/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip list
COPY . /ApprodoBot_dev
CMD ["python","main.py"]