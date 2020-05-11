FROM alpine:3.11

ENV TERRAFORM_VERSION=0.12.24
ENV ANSIBLE_VERSION=2.8.1
ENV OPENSTACKCLIENT_VERSION=3.17.0
ENV HELM_VERSION=3.2.1
ENV KUBERNETES_VERSION=v1.15.11
ENV PYYAML_VERSION=5.1.1
ENV JINJA2_VERSION=2.10.3 

ENV PIP=19.3.1

SHELL ["/bin/ash", "-o", "pipefail", "-c"]

# Install dependencies

RUN apk --update add python3 py-pip openssh-client bash curl openssl ca-certificates && \
    apk --update add --virtual build-dependencies \
                python-dev libffi-dev openssl-dev build-base  && \
    pip install --upgrade pip cffi && \
    pip install --no-cache-dir \
      python-openstackclient=="$OPENSTACKCLIENT_VERSION" \
      ansible=="$ANSIBLE_VERSION" && \
    pip3 install --no-cache-dir \
      PyYAML=="$PYYAML_VERSION" \
      jinja2=="$JINJA2_VERSION" && \
    apk del build-dependencies && \
    rm -rf /var/cache/apk/*

# Install Terraform
RUN curl "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" > \
    "terraform_${TERRAFORM_VERSION}_linux_amd64.zip" && \
    unzip "terraform_${TERRAFORM_VERSION}_linux_amd64.zip" -d /usr/local/bin && \
    rm -f "terraform_${TERRAFORM_VERSION}_linux_amd64.zip"

# Install Helm
RUN curl "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz" > \
    "helm-v${HELM_VERSION}-linux-amd64.tar.gz" && \
    tar xzf "helm-v${HELM_VERSION}-linux-amd64.tar.gz" && \
    mv linux-amd64/helm /usr/local/bin/helm && \
    rm -rf "linux-amd64" "helm-v${HELM_VERSION}-linux-amd64.tar.gz"

# Install Kubernetes client
RUN curl "https://storage.googleapis.com/kubernetes-release/release/${KUBERNETES_VERSION}/bin/linux/amd64/kubectl" > \
    /usr/local/bin/kubectl && \
    chmod +x /usr/local/bin/kubectl
