module Api
  module V1
    # GET /api/v1/me — the learner's own profile: XP, ratings by skill, linked sign-in.
    # PATCH /api/v1/me — sets the learner's level.
    # DELETE /api/v1/me — deletes the account and everything personal in it.
    class MeController < BaseController
      PROVISIONAL_BELOW = 10

      def show
        ratings = current_user.skill_ratings.order(:skill).map do |r|
          { skill: r.skill, rating: r.rating.round, attempts: r.attempts, correct: r.correct,
            provisional: r.attempts < PROVISIONAL_BELOW }
        end
        identity = current_user.identities.first
        render json: { handle: current_user.handle, anonymous: current_user.anonymous, xp: current_user.xp, ratings: ratings,
                       account: identity && { provider: identity.provider, name: identity.name }, level: current_user.level }
      end

      # PATCH /api/v1/me {level} — who the learner is studying as; what is written for them from now on.
      def update
        level = params.require(:level).to_s
        return render(json: { error: "invalid_level" }, status: :unprocessable_entity) unless Level.valid?(level)

        current_user.update!(level: level)
        render json: { level: level }
      end

      # Shared questions the learner helped create stay in the bank (they hold nothing personal);
      # answers already counted in crowd tallies stay as anonymous counts.
      def destroy
        current_user.destroy!
        head :no_content
      end
    end
  end
end
