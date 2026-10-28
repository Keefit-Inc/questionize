module ApplicationCable
  # Browsers cannot set headers on WebSocket requests, so clients pass their bearer token
  # as ?token= when connecting to /cable.
  class Connection < ActionCable::Connection::Base
    identified_by :current_user

    def connect
      self.current_user = User.find_by(api_token: request.params[:token].to_s) || reject_unauthorized_connection
    end
  end
end
