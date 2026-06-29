.PHONY: build test dev doctor lint clean

PYTHON_PACKAGES := \
	python/tpt_catalyst \
	python/tpt_alloy \
	python/tpt_element \
	python/tpt_fusion \
	python/tpt_emulator \
	python/tpt_mosaic \
	python/tpt_drivers \
	python/tpt_train \
	python/tpt_silicon \
	python/tpt_photon \
	python/tpt_pulse \
	python/tpt_shell \
	python/tpt_fl

# Build Rust crates and maturin-backed Python packages, then install all Python packages
build:
	cargo build --release
	cd python/tpt_catalyst && maturin develop
	cd python/tpt_alloy && maturin develop
	@for pkg in $(PYTHON_PACKAGES); do \
		if [ "$$pkg" != "python/tpt_catalyst" ] && [ "$$pkg" != "python/tpt_alloy" ]; then \
			echo "Installing $$pkg..."; \
			pip install -e "$$pkg"; \
		fi \
	done

# Run all tests: Rust, Python, and Go
test:
	cargo test --all
	pytest python -v
	cd services/tpt-observer && go test ./...
	cd services/synthesis-worker && go test ./...
	cd services/synthesis-broker && go test ./...

# Run integration tests only
test-integration:
	pytest tests/integration -v -m integration

# Start Observer backend + frontend concurrently
dev:
	@echo "Starting Observer backend on :8080 and frontend on :3000..."
	cd services/tpt-observer && go run ./cmd/observer & \
	cd frontend && npm run dev

# Run tpt-doctor toolchain readiness check
doctor:
	@python -c "from tpt_catalyst.doctor import run_doctor; run_doctor()" || \
		echo "Run 'make build' first to install tpt-catalyst"

# Lint: Rust fmt check, Python ruff, Go vet, and frontend eslint
lint:
	cargo fmt --all -- --check
	cargo clippy --all -- -D warnings
	ruff check python
	@for svc in services/tpt-observer services/synthesis-worker services/synthesis-broker services/crucible-cloud; do \
		echo "go vet $$svc..."; \
		cd $$svc && go vet ./...; cd -; \
	done
	cd frontend && npm run lint

# Remove build artifacts
clean:
	cargo clean
	find python -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find python -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/.next
