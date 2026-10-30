module Research
  class ScheduleJob < ApplicationJob
    queue_as :research

    def perform
      StartCycle.call(automatic: true)
    rescue StartCycle::Unavailable => e
      Rails.logger.info("[Research::ScheduleJob] #{e.message}")
    end
  end
end
