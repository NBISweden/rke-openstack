FROM ubuntu:bionic-20190204

# Terraform and Openstack client versions
ENV TERRAFORM_VERSION=0.12.7
ENV ANSIBLE_VERSION=2.8.1
ENV OPENSTACKCLIENT_VERSION=3.17.0
ENV HELM_VERSION=2.14.3
ENV KUBERNETES_VERSION=v1.15.3

# PIP version
ENV PIP=9.0.3

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install dependencies
RUN apt update -y && \
      DEBIAN_FRONTEND=noninteractive apt install -y \
      apt-transport-https \
      curl \
      git \
      jq \
      openssl \
      python-pip \
      unzip && \
    pip install --no-cache-dir --upgrade pip=="${PIP}" && \
    pip install --no-cache-dir \
      python-openstackclient=="$OPENSTACKCLIENT_VERSION" \
      ansible=="$ANSIBLE_VERSION" && \
    rm -rf /usr/lib/gcc && \
    rm -rf /usr/share/man && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

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
