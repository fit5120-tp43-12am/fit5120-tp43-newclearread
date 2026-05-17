ARG VLLM_BASE_IMAGE=vllm/vllm-openai:latest
FROM ${VLLM_BASE_IMAGE}

# The selected base model is a BitsAndBytes 4-bit checkpoint.
# Install explicitly so the production image does not depend on whether
# the upstream vLLM image happens to include this optional package.
RUN python3 -m pip install --no-cache-dir "bitsandbytes>=0.46.1"
