.PHONY: snapshot

snapshot:
ifndef PASSED
	$(error Usage: make snapshot PASSED=<pytest_pass_count>)
endif
	./scripts/update_handoff_snapshot.sh --pytest-passed $(PASSED)
