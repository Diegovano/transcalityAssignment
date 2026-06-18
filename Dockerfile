FROM amazonlinux:2 AS sumo-builder
RUN yum install -y yum-utils
RUN amazon-linux-extras install epel -y
RUN yum-config-manager --add-repo=https://download.opensuse.org/repositories/science:/dlr/CentOS_7/
# RUN cd /etc/yum.repos.d/
# RUN curl -L --remote-name https://download.opensuse.org/repositories/science:dlr/CentOS_7/science:dlr.repo
RUN yum install -y --nogpgcheck sumo-1.27.0

RUN mkdir /sumo-libs
RUN ldd /usr/bin/sumo /usr/bin/netconvert \
    | grep -Po "(?<==> ).*\\.so[^\\s]*" \
    | sort -u \
    | xargs -I{} cp {} /sumo-libs/


FROM public.ecr.aws/lambda/python:3.11 AS base
COPY --from="sumo-builder" /sumo-libs/ /usr/lib64/
COPY --from="sumo-builder" /usr/bin/sumo /usr/bin/netconvert /usr/bin/duarouter /usr/bin/

COPY handlers/*  /var/task/
COPY s3helper.py /var/task/
COPY test.zip /var/task
