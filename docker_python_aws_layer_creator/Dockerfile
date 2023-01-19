FROM amazonlinux:2018.03
RUN ulimit -n 1024 && yum -y update && yum -y install \
		python38 \
		python38-pip \
		python38-devel \
		zip \
		&& yum clean all

RUN python3 -m pip install pip==22.1.2
RUN pip install virtualenv==20.14.1