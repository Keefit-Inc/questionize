# Internal AI service (ai/). Rails jobs are its only caller.
Rails.application.configure do
  config.x.ai_service.url = ENV.fetch("AI_SERVICE_URL", "http://localhost:8000")
  config.x.ai_service.token = ENV.fetch("AI_INTERNAL_TOKEN", "")
  config.x.ai_service.read_timeout = Integer(ENV.fetch("AI_SERVICE_READ_TIMEOUT", "600"))
end
