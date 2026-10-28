module Api
  module V1
    class FeedbacksController < BaseController
      # POST /api/v1/items/:item_id/feedback {kind: up|down|flag, reason, comment}
      # Only learners who have answered the item can rate or flag it.
      def create
        item = Item.accessible_by(current_user).includes(:current_version).find_by!(public_id: params[:item_id])
        return render(json: { error: "answer_first" }, status: :forbidden) unless Learning::Attempt.exists?(user: current_user, item: item)

        feedback = Feedback.find_or_initialize_by(user: current_user, item_version: item.current_version, kind: params.require(:kind).to_s)
        feedback.update!(reason: params[:reason].presence, comment: params[:comment].to_s.strip.presence)
        trigger = Quality::Triggers.check(item) if feedback.kind == "flag"
        render json: { recorded: feedback.kind, review_started: trigger.present? }, status: :created
      rescue ActiveRecord::RecordInvalid => e
        render json: { error: "invalid_feedback", details: e.record.errors.full_messages }, status: :unprocessable_entity
      end
    end
  end
end
