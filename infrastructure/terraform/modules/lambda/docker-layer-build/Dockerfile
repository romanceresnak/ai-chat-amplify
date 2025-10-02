FROM public.ecr.aws/lambda/python:3.11

# Copy requirements
COPY requirements.txt .

# Install dependencies for Lambda
RUN pip install -r requirements.txt -t /opt/python/

# Create the final layer
FROM scratch
COPY --from=0 /opt/python /opt/python