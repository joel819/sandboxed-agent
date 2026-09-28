# Built with full network access (normal `docker build`). OpenShell's policy only
# restricts the *running* sandbox - dependencies must already be baked in, since
# policy.yaml has no route to PyPI at runtime.
FROM python:3.12-slim

RUN useradd -m -u 1500 sandbox
RUN pip install --no-cache-dir chromadb requests

# decoy credential file, purely so demo scenario 2 hits a real Landlock DENY
# instead of a meaningless "No such file" - never a real key.
RUN mkdir -p /home/sandbox/.ssh \
    && echo "-----BEGIN OPENSSH PRIVATE KEY----- (decoy, not a real key)" > /home/sandbox/.ssh/id_rsa \
    && chown -R sandbox:sandbox /home/sandbox/.ssh && chmod 600 /home/sandbox/.ssh/id_rsa

WORKDIR /app
COPY agent.py tools.py setup_data.py groq_adapter.py run_agent.py ./

# seed orders.db + chroma_db now, while we still have full network/filesystem access
RUN python3 setup_data.py

RUN chown -R sandbox:sandbox /app
USER sandbox

ENTRYPOINT ["python3", "run_agent.py"]
