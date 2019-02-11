FROM ubuntu:bionic-20190204

# Terraform and Openstack client versions
ENV TERRAFORM_VERSION=0.11.11
ENV OPENSTACKCLIENT_VERSION=3.17.0
# Terraform plugin versions
ENV PLUGIN_OPENSTACK=1.15.1
ENV PLUGIN_RKE=0.7.0
ENV PLUGIN_KUBERNETES=1.5.0

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
      python-openstackclient=="$OPENSTACKCLIENT_VERSION" && \
    rm -rf /usr/lib/gcc && \
    rm -rf /usr/share/man && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Install Terraform
RUN curl "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" > \
    "terraform_${TERRAFORM_VERSION}_linux_amd64.zip" && \
    unzip "terraform_${TERRAFORM_VERSION}_linux_amd64.zip" -d /bin && \
    rm -f "terraform_${TERRAFORM_VERSION}_linux_amd64.zip"

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

RUN curl -sL "https://github.com/yamamoto-febc/terraform-provider-rke/releases/download/${PLUGIN_RKE}/terraform-provider-rke_${PLUGIN_RKE}_linux-amd64.zip" > \
    "terraform-provider-rke_${PLUGIN_RKE}_linux_amd64.zip" && \
    unzip "terraform-provider-rke_${PLUGIN_RKE}_linux_amd64.zip" -d /terraform_plugins/ && \
    rm -f "terraform-provider-rke_${PLUGIN_RKE}_linux_amd64.zip"
