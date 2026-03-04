FROM docker.io/siddhiio/siddhi-runner-alpine:5.1.2

USER root

# Install MQTT extension (not bundled in the base runner image)
RUN apk add --no-cache wget \
 && SIDDHI_LIB="/home/siddhi_user/siddhi-runner/lib" \
 && wget -q -P "${SIDDHI_LIB}/" \
      "https://repo1.maven.org/maven2/io/siddhi/extension/io/mqtt/siddhi-io-mqtt/3.0.4/siddhi-io-mqtt-3.0.4.jar" \
 && wget -q -P "${SIDDHI_LIB}/" \
      "https://repo1.maven.org/maven2/org/eclipse/paho/org.eclipse.paho.client.mqttv3/1.2.5/org.eclipse.paho.client.mqttv3-1.2.5.jar" \
 && apk del wget

USER siddhi_user

COPY --chown=siddhi_user apps/*.siddhi \
     /home/siddhi_user/siddhi-runner/deployment/siddhi-files/
