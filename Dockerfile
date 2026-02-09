FROM python:3.12
WORKDIR /ApprodoBot
COPY requirements.txt /ApprodoBot/
RUN pip install -r requirements.txt
COPY . /ApprodoBot
CMD ["python","ApprodoBot.py"]