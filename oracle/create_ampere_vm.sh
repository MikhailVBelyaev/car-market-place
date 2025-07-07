#!/bin/bash

COMPARTMENT_ID="ocid1.tenancy.oc1..aaaaaaaajeyct7efelj4bhwom5pnee4one3mtbjbrmdm7tqpfhfi56mz2eya"
SUBNET_ID="ocid1.subnet.oc1.iad.aaaaaaaas52hzdvziti5oegymjbzezlu5sccevo5kuf5jvmyn4w4yhzpsbwa"
IMAGE_OCID="ocid1.image.oc1.iad.aaaaaaaav5ph4cfq3ifg47pb6d7jk4zix2gmuqwwjwbqjqv7bsb5gzy3l7eq"
AVDS=("jLCH:US-ASHBURN-AD-1" "jLCH:US-ASHBURN-AD-2" "jLCH:US-ASHBURN-AD-3")

# Read your public key
# Safely encode SSH key
PUB_KEY_PATH="$HOME/.ssh/id_rsa.pub"

if [[ ! -s "$PUB_KEY_PATH" ]]; then
  echo "❌ Public SSH key not found or empty at $PUB_KEY_PATH"
  exit 1
fi

PUB_KEY=$(cat "$PUB_KEY_PATH" | jq -Rsa .)

for AD in "${AVDS[@]}"; do
  echo "Trying $AD..."

  {
    oci compute instance launch \
      --debug \
      --availability-domain "$AD" \
      --compartment-id "$COMPARTMENT_ID" \
      --shape "VM.Standard.A1.Flex" \
      --display-name "ampere-auto" \
      --metadata "{\"ssh_authorized_keys\": $PUB_KEY}" \
      --source-details "{\"sourceType\":\"image\",\"imageId\":\"$IMAGE_OCID\"}" \
      --shape-config '{"ocpus": 1, "memoryInGBs": 6}' \
      --subnet-id "$SUBNET_ID"
  } && echo "✅ Success in $AD" && break

  echo "❌ Failed in $AD, trying next..."
  sleep 10
done