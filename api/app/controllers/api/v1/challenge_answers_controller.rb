module Api
  module V1
    class ChallengeAnswersController < BaseController
      # POST /api/v1/maps/:map_id/challenges/:challenge_id/answer {choice}
      # The first answer counts; it unlocks the judged answer and what other readers chose.
      def create
        run = GenerationRun.completed_maps.find(params[:map_id])
        index = params[:challenge_id].to_i
        return head(:not_found) unless Array(run.result["challenges"]).any? { _1["index"] == index }

        choice = params.require(:choice).to_s.upcase
        Learning::ChallengeAnswer.create_with(choice: choice).find_or_create_by!(user: current_user, generation_run: run, challenge_index: index)
        challenge = MapPayload.new(run, user: current_user).as_json[:challenges].find { _1[:index] == index }
        render json: challenge, status: :created
      rescue ActiveRecord::RecordInvalid
        render json: { error: "invalid_choice" }, status: :unprocessable_entity
      end
    end
  end
end
