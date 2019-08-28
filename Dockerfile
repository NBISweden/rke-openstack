FROM ubuntu:bionic-20190204

# Terraform and Openstack client versions
ENV TERRAFORM_VERSION=0.12.7
ENV ANSIBLE_VERSION=2.8.1
ENV OPENSTACKCLIENT_VERSION=3.17.0
ENV HELM_VERSION=2.14.3
ENV KUBERNETES_VERSION=v1.15.3
# Terraform plugin versions
ENV PLUGIN_OPENSTACK=1.21.1
ENV PLUGIN_RKE=0.14.1
ENV PLUGIN_KUBERNETES=1.8.1
ENV PLUGIN_NULL=2.1.2
ENV PLUGIN_LOCAL=1.3.0
ENV PLUGIN_TEMPLATE=2.1.2
ENV PLUGIN_RANDOM=2.2.0

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

# Install Terraform plugins
RUN mkdir -p /terraform_plugins
RUN curl "https://releases.hashicorp.com/terraform-provider-openstack/${PLUGIN_OPENSTACK}/terraform-provider-openstack_${PLUGIN_OPENSTACK}_linux_amd64.zip" > \
    "terraform-provider-openstack_${PLUGIN_OPENSTACK}_linux_amd64.zip" && \
    unzip "terraform-provider-openstack_${PLUGIN_OPENSTACK}_linux_amd64.zip" -d /terraform_plugins/ && \
    rm -f "terraform-provider-openstack_${PLUGIN_OPENSTACK}_linux_amd64.zip"

RUN curl "https://releases.hashicorp.com/terraform-provider-kubernetes/${PLUGIN_KUBERNETES}/terraform-provider-kubernetes_${PLUGIN_KUBERNETES}_linux_amd64.zip" > \
    "terraform-provider-kubernetes_${PLUGIN_KUBERNETES}_linux_amd64.zip" && \
    unzip "terraform-provider-kubernetes_${PLUGIN_KUBERNETES}_linux_amd64.zip" -d /terraform_plugins/ && \
    rm -f "terraform-provider-kubernetes_${PLUGIN_KUBERNETES}_linux_amd64.zip"

RUN curl "https://releases.hashicorp.com/terraform-provider-null/${PLUGIN_NULL}/terraform-provider-null_${PLUGIN_NULL}_linux_amd64.zip" > \
    "terraform-provider-null_${PLUGIN_NULL}_linux_amd64.zip" && \
    unzip "terraform-provider-null_${PLUGIN_NULL}_linux_amd64.zip" -d /terraform_plugins/ && \
    rm -f "terraform-provider-null_${PLUGIN_NULL}_linux_amd64.zip"

RUN curl "https://releases.hashicorp.com/terraform-provider-local/${PLUGIN_LOCAL}/terraform-provider-local_${PLUGIN_LOCAL}_linux_amd64.zip" > \
    "terraform-provider-local_${PLUGIN_LOCAL}_linux_amd64.zip" && \
    unzip "terraform-provider-local_${PLUGIN_LOCAL}_linux_amd64.zip" -d /terraform_plugins/ && \
    rm -f "terraform-provider-local_${PLUGIN_LOCAL}_linux_amd64.zip"

RUN curl -sL "https://github.com/yamamoto-febc/terraform-provider-rke/releases/download/${PLUGIN_RKE}/terraform-provider-rke_${PLUGIN_RKE}_linux-amd64.zip" > \
    "terraform-provider-rke_${PLUGIN_RKE}_linux_amd64.zip" && \
    unzip "terraform-provider-rke_${PLUGIN_RKE}_linux_amd64.zip" -d /terraform_plugins/ && \
    rm -f "terraform-provider-rke_${PLUGIN_RKE}_linux_amd64.zip"

RUN curl "https://releases.hashicorp.com/terraform-provider-template/${PLUGIN_TEMPLATE}/terraform-provider-template_${PLUGIN_TEMPLATE}_linux_amd64.zip" > \
    "terraform-provider-template_${PLUGIN_TEMPLATE}_linux_amd64.zip" && \
    unzip "terraform-provider-template_${PLUGIN_TEMPLATE}_linux_amd64.zip" -d /terraform_plugins/ && \
    rm -f "terraform-provider-template_${PLUGIN_TEMPLATE}_linux_amd64.zip"

RUN curl "https://releases.hashicorp.com/terraform-provider-random/${PLUGIN_RANDOM}/terraform-provider-random_${PLUGIN_RANDOM}_linux_amd64.zip" > \
    "terraform-provider-random_${PLUGIN_RANDOM}_linux_amd64.zip" && \
    unzip "terraform-provider-random_${PLUGIN_RANDOM}_linux_amd64.zip" -d /terraform_plugins/ && \
    rm -f "terraform-provider-random_${PLUGIN_RANDOM}_linux_amd64.zip"
