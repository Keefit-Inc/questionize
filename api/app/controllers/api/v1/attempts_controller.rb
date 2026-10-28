module Api
  module V1
    class AttemptsController < BaseController
      # POST /api/v1/items/:item_id/attempts {label, time_ms}
      def create
        item = Item.accessible_by(current_user).includes(:current_version, :source).find_by!(public_id: params[:item_id])
        label = params.require(:label).to_s.upcase
        return render(json: { error: "invalid_label" }, status: :unprocessable_entity) unless ItemVersion::LABELS.include?(label)

        result = Learning::RecordAttempt.call(user: current_user, item: item, chosen_label: label, time_ms: params[:time_ms]&.to_i)
        item.reload
        ItemChannel.broadcast_tally(item)
        render json: {
          correct: result.attempt.correct,
          rated: result.attempt.rated,
          rating_changes: result.rating_changes,
          xp_awarded: result.xp_awarded,
          item: ItemPayload.new(item, revealed: true).as_json
        }, status: :created
      end
    end
  end
end
