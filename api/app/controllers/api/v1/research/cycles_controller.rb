module Api
  module V1
    module Research
      class CyclesController < BaseController
        rate_limit to: 2, within: 1.minute, only: :create, by: -> { current_user.id }

        def create
          return render(json: { error: "curator_required" }, status: :forbidden) unless current_user.curator

          cycle = ::Research::StartCycle.call(requested_by: current_user)
          render json: { id: cycle.public_id, status: cycle.status, cycle: cycle.public_data }, status: :accepted
        rescue ::Research::StartCycle::Unavailable => e
          render json: { error: "cycle_unavailable", message: e.message }, status: :conflict
        end
      end
    end
  end
end
