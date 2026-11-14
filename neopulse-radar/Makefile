.PHONY: install test lint demo app record briefing validate check
install:
	pip install -r requirements.txt && pip install -e .
test:
	pytest
lint:
	ruff check src tests
demo:      ## sinh dữ liệu mô phỏng 6 phiên vào data/neopulse.sqlite
	neopulse simulate --sessions 6 --reset
app:
	streamlit run src/neopulse/app/dashboard.py
check:     ## kiểm tra cấu hình + kết nối NEO API (không in bí mật)
	neopulse check
record:    ## ghi luồng WebSocket thật (cần .env, NEOPULSE_MODE=live)
	neopulse record
briefing:
	neopulse briefing
validate:
	neopulse validate
