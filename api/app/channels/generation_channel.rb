# Live agent progress for one generation run, visible only to the user who started it.
class GenerationChannel < ApplicationCable::Channel
  def subscribed
    run = GenerationRun.find_by(id: params[:run_id], user: current_user)
    run ? stream_for(run) : reject
  end
end
