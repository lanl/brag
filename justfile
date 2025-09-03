export TOKENIZERS_PARALLELISM := "true"
export ALLOW_RESET := "TRUE"
export ANONYMIZED_TELEMETRY := "FALSE"

mode := "dev"
vllm-llm-port := "8200"
vllm-emb-port := "8201"
ollama-port := "11434" # "8202"
litellm-port := "8203"
chroma-port := "8204"

litellm-url := "http://localhost:" + litellm-port
chunksize := "512"
chunk_overlap := "100"
batchsize := "64"
num-retrieve := "10"
temperature := "0.2"
logging := "info"

appdata-dir := ".brag"
demo-corpus-dir := appdata-dir / "demo-corpus"

# CharlieCloud
load := "module load charliecloud && "
ch-convert :=  load + "ch-convert"
ch-image  := load + "ch-image"
ch-run  := load + "ch-run"
version := "v" + `uv version --short`
tag := `arch` + "-" + version
sqfs-path := "sqfs" / "brag-" + tag + ".sqfs"
ch-port := if `arch` == "aarch64" {
    "8305"
} else {
    "8205"
}

# These are the LAUR-ed LANL policies.
corpus := if mode == "prod" {
    "lanl-policies-released"
} else {
    "demo-corpus"
}

corpus-dir := appdata-dir / corpus
rag-type := "brag" # or "trag"

# vllm-emb := "hosted_vllm/intfloat/e5-large-v2" # context window too small (512)
# vllm-emb := "hosted_vllm/intfloat/e5-mistral-7b-instruct" # too large.
# vllm-emb := "hosted_vllm/nvidia/NV-embed-v2" # too large.
vllm-emb := "hosted_vllm/BAAI/bge-m3"
ollama-emb := "ollama/nomic-embed-text"

openai-llm := "openai/gpt-4o-mini"
ollama-llm := "ollama_chat/llama3.1:8b"
vllm-llm := "hosted_vllm/meta-llama/Llama-3.1-8B-Instruct"

tool-chat-template := if vllm-llm == "meta-llama/Llama-3.1-8B-Instruct" {
    "tool_chat_template_llama3.1_json.jinja"
} else if vllm-llm == "meta-llama/Llama-3.2-1B-Instruct" {
    "tool_chat_template_llama3.2_pythonic.jinja"
} else if vllm-llm == "meta-llama/Llama-3.2-3B-Instruct" {
    "tool_chat_template_llama3.2_pythonic.jinja"
} else {
    "not-implemented"
}

tool-call-parser := if vllm-llm == "meta-llama/Llama-3.1-8B-Instruct" {
    "llama3_json"
} else if vllm-llm == "meta-llama/Llama-3.2-1B-Instruct" {
    "pythonic"
} else if vllm-llm == "meta-llama/Llama-3.2-3B-Instruct" {
    "pythonic"
} else {
    "not-implemented"
}

llm-flags := if mode == "prod" {
    " "
} else {
    "--llm=" + ollama-llm + " "
}

# "--emb=openai/nomic " +
# "--emb-base-url=https://lanl-policy-emb.dev.aws.lanl.gov " +
# "--emb-api-key=$PRAG_EMB_API_KEY " +
# "--no-ssl-verify"
emb-flags := if mode == "prod" {
    " "
} else {
    "--emb=" + ollama-emb + " "
}

@help:
    just -l -u

show-api-flags:
    echo {{ llm-flags }}
    echo {{ emb-flags }}

# NOTE:
# llama3.1 (8b and 70b) and llama3.2 (1b and 3b) have context windows of 128K tokens
# BAAI/bge-m3 has a context window of 8192

db-name := corpus
db-dir := appdata-dir / "db" / corpus / mode

fmt:
    ruff format
    just --fmt --unstable

make-demo-corpus-dir:
    mkdir -p {{ demo-corpus-dir }}

demo-corpus: make-demo-corpus-dir
    curl https://arxiv.org/pdf/2106.05403 -o {{ demo-corpus-dir }}/aibd.pdf
    curl https://www.gutenberg.org/cache/epub/1342/pg1342.txt -o {{ demo-corpus-dir }}/pride-and-prejudice.txt
    curl https://proceedings.neurips.cc/paper_files/paper/2017/file/3f5ee243547dee91fbd053c1c4a845aa-Paper.pdf -o {{ demo-corpus-dir }}/attention-is-all-you-need.pdf

list-openai-models:
    curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"

clean: clean-db

clean-db:
    uv run brag rm-index \
      --db-name={{ db-name }} --db-dir={{ db-dir }} --log=info
    rm -rf {{ db-dir }}

# Index from command line
@index *flags:
    uv run brag index --corpus-dir {{ corpus-dir }} \
      --db-name={{ db-name }} --db-dir={{ db-dir }} \
      --batchsize={{ batchsize }} {{ flags }} \
      {{ llm-flags }}

# Search from command line
@search *flags:
    uv run brag search \
      --corpus-dir={{ corpus-dir }} --db-dir={{ db-dir }} \
      --db-name={{ db-name }} --db-dir={{ db-dir }} {{ flags }} \
      {{ emb-flags }}

# RAG from the command line.
ask *flags:
    uv run brag ask \
      --temperature={{ temperature }} \
      --corpus-dir={{ corpus-dir }} \
      --batchsize={{ batchsize }} \
      --chunk-size={{ chunksize }} \
      --chunk-overlap={{ chunk_overlap }} \
      --num-retrieved-docs={{ num-retrieve }} \
      --db-name={{ db-name }} --db-dir={{ db-dir }} \
      --log={{ logging }} {{ flags }} \
      --rag-type {{ rag-type }} \
      {{ llm-flags }} {{ emb-flags }}

# RAG from the command line.
# Chat from the command line.
chat *flags:
    uv run brag chat --log={{ logging }} \
        {{ flags }} {{ llm-flags }} {{ emb-flags }}

serve-ollama:
    OLLAMA_HOST=0.0.0.0:{{ ollama-port }} ollama serve

# Requires running tool-template before.
serve-vllm-llm:
    vllm serve \
      "{{ vllm-llm }}" \
      --dtype half --port={{ vllm-llm-port }} \
      --api-key=1234 --max-model-len 128000 \
      --enable-auto-tool-choice \
      --tool-call-parser={{ tool-call-parser }} \
      --chat-template templates/tool-chat-templates/{{ tool-chat-template }}

serve-vllm-emb:
    vllm serve "{{ vllm-emb }}" --port={{ vllm-emb-port }} \
      --trust-remote-code --task=embed --api-key=1234 --enforce-eager \
      --dtype half

tool-template:
    mkdir -p templates/tool-chat-templates
    wget https://raw.githubusercontent.com/vllm-project/vllm/refs/heads/main/examples/{{ tool-chat-template }}
    mv {{ tool-chat-template }} templates/tool-chat-templates

# Sync git tag with package tag. 
tag:
    git tag "v$(uv version --short)"
    git push --tags

# Update python package version. You will need to run `just tag` after to add a git tag.
[confirm("Have you updated changes.md, README.md, and misc/brag-ask-help.txt (y/n)?")]
bump kind:
    uv version --bump {{ kind }}
    @echo "Remember to run {{ CYAN }}just tag{{ NORMAL }} after committing."

save-brag-ask-help:
    uv run brag ask -h > misc/brag-ask-help.txt

serve-litellm:
  litellm --config config/demo-config.yaml --port={{ litellm-port }}

serve-chroma:
  uv run chroma run --port={{ chroma-port }} --path={{ db-dir }}

serve window-name="llm-servers":
  tmux new-window -n {{ window-name }} "just serve-vllm-llm"
  tmux split-window -h -t {{ window-name }} "just serve-vllm-emb"
  tmux split-window -h -t {{ window-name }} "just serve-litellm"
  tmux split-window -h -t {{ window-name }} "just serve-chroma"
  tmux select-layout -t {{ window-name }} even-vertical


clean-litellm:
    uv run brag rm-index \
      --db-name={{ db-name }} \
      --db-dir={{ appdata-dir }}/db/{{ corpus }}/litellm \
      --db-port={{ chroma-port }} \
      --log=info --reset


ask-litellm *flags:
    uv run brag ask \
      --temperature={{ temperature }} \
      --corpus-dir {{ corpus-dir }} \
      --batchsize={{ batchsize }} \
      --chunk-size={{ chunksize }} \
      --chunk-overlap={{ chunk_overlap }} \
      --num-retrieved-docs={{ num-retrieve }} \
      --db-name={{ db-name }} \
      --db-dir={{ appdata-dir }}/db/{{ corpus }}/litellm \
      --db-port={{ chroma-port }} \
      --log={{ logging }} {{ flags }} \
      --rag-type {{ rag-type }} \
      --base-url={{ litellm-url }} \
      --emb-base-url={{ litellm-url }} \
      --llm=llama8b \
      --emb=bge-m3 \
      {{ flags }}

list-litellm:
    curl {{ litellm-url }}/v1/models \
        -H "Authorization: Bearer anything"

test *flags:
    uv run brag ask --corpus-dir=.brag/demo-corpus --db-dir=.brag/db/test {{ flags }}

clean-test *flags:
    rm -rf .brag/db/test
    just test {{ flags }}

## Conda.
# Create conda environment with current source.
conda-env tag="latest-x86":
    conda create -n brag-{{ tag }} python=3.12 -y
    conda run --live-stream -n brag-{{ tag }} pip install .
    conda run --live-stream -n brag-{{ tag }} pip install 'litellm[proxy]'

# Remove conda environment.
conda-clean tag="latest-x86":
    conda env remove -n brag-{{ tag }}

[doc("""
Bundle environment into an archive. Requires conda-pack (see:
https://conda.github.io/conda-pack/

Note that the conda environment needs to first exist. So 
you may need to first run `just conda-env`
""")]
conda-pack tag="latest-x86":
    conda pack -n brag-{{ tag }}
    mkdir -p output
    mv brag-{{ tag }}.tar.gz output/brag-{{ tag }}.tgz

# Build conda archive after building (clean) conda environment.
conda-clean-pack tag="latest-x86":
    just conda-clean {{ tag }}
    just conda-env {{ tag }}
    just conda-pack {{ tag }}

### Charliecloud build instructions ###

# Build brag image through charliecloud. Requires being on target platform (e.g., x86 or aarch64). Use --rebuild to force rebuild.
build flags="":
    mkdir -p sqfs
    unset CH_IMAGE_USERNAME CH_IMAGE_PASSWORD CH_IMAGE_AUTH && \
    {{ ch-image }} build {{ flags }} \
    -t brag:{{ tag }} .
    {{ ch-convert }} brag:{{ tag }} {{ sqfs-path }}

# Remove compiled sqfs file.
[confirm("Remove *.sqfs? (y/n)")]
clean-sqfs:
    {{ ch-image }} reset
    rm -f *.sqfs

# Run brag image shell.
image-shell:
    {{ ch-run }} -W {{ sqfs-path }} --cd=/app --set-env -- bash

# List port info.
port-info:
    ss -talnp

# Run brag container.
image-run cache-dir=".brag-ch":
    mkdir -p {{ cache-dir }} .gradio
    {{ ch-run }} {{ sqfs-path }} \
        -c /app \
        --set-env="OPENAI_API_KEY=$OPENAI_API_KEY" \
        --set-env \
        -b .gradio:/app/.gradio \
        -b {{ cache-dir }}:/app/.brag -- \
        brag ask --corpus-dir=/app/.brag/demo-corpus --port={{ ch-port }}

# Push image onto lisdi-registry. 
push-registry:
    {{ ch-image }} push brag:{{ tag }} lisdi-registry.lanl.gov/alui/brag:{{ tag }}

image-list:
    {{ ch-image }} list

# Print python package and latest git tag (to see if they match).
@version-info:
    echo "Python package: v$(uv version --short)"
    echo "Latest Git tag: $(git describe --abbrev=0 --tags)"
