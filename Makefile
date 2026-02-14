.PHONY: snapshot handoff-quickview handoff-prepend

snapshot:
ifndef PASSED
	$(error Usage: make snapshot PASSED=<pytest_pass_count>)
endif
	./scripts/update_handoff_snapshot.sh --pytest-passed $(PASSED)

handoff-quickview:
	./.venv/bin/python scripts/handoff_helper.py quickview --file $${FILE:-todo/NEXT_MACHINE_HANDOFF.md}

handoff-prepend:
ifndef SUMMARY
	$(error Usage: make handoff-prepend SUMMARY="Completed ...:" [FILE=todo/NEXT_MACHINE_HANDOFF.md])
endif
	./.venv/bin/python scripts/handoff_helper.py prepend-recent --file $${FILE:-todo/NEXT_MACHINE_HANDOFF.md} --summary "$(SUMMARY)"
