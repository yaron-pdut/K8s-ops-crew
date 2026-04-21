.PHONY: install lint format test kind-up kind-down run clean

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------
install:
	pip install -e ".[dev]" --index-url https://pypi.org/simple/ --extra-index-url https://pypi.org/simple/ 

lint:
	ruff check k8s_ops_crew tests
	black --check k8s_ops_crew tests

format:
	ruff check --fix k8s_ops_crew tests
	black k8s_ops_crew tests

test:
	pytest

test-fast:
	pytest -x --no-cov

# ---------------------------------------------------------------------------
# kind cluster
# ---------------------------------------------------------------------------
kind-up:
	kind create cluster --name k8s-ops-crew --config infra/kind-cluster.yaml
	kubectl apply -f infra/rbac/serviceaccount.yaml
	kubectl apply -f infra/rbac/clusterrole.yaml
	kubectl apply -f infra/rbac/clusterrolebinding.yaml
	@echo "✅  kind cluster 'k8s-ops-crew' is ready"

kind-down:
	kind delete cluster --name k8s-ops-crew

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
run:
	python -m k8s_ops_crew "Give me a health summary of the current cluster"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
