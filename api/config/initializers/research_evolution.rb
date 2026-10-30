Rails.application.configure do
  config.x.research_evolution.enabled = ENV.fetch("RESEARCH_EVOLUTION_ENABLED", "false") == "true"
  config.x.research_evolution.min_trusted_sources = 3
  config.x.research_evolution.min_rated_attempts = 20
  config.x.research_evolution.cooldown_seconds = 24.hours.to_i
  config.x.research_evolution.daily_limit = 2
end
