Rails.application.routes.draw do
  # Health check for kamal-proxy and uptime monitors.
  get "up" => "rails/health#show", as: :rails_health_check

  # The web app's shell, never cached (see SpaController).
  root "spa#show"

  # Shared question links get social preview tags.
  get "q/:public_id", to: "share_pages#show", as: :share_page

  namespace :api do
    namespace :v1 do
      resources :devices, only: :create
      resources :generations, only: %i[create show]
      resources :maps, only: %i[create show] do
        resources :challenges, only: [] do
          resource :answer, only: :create, controller: "challenge_answers"
        end
      end
      resource :me, only: :show, controller: "me"
      post "me/eligibility", to: "eligibility#create", as: :eligibility
      resources :error_log, only: %i[index show create], controller: "error_log" do
        get :question, on: :member
      end
      resources :items, only: %i[index show] do
        resources :attempts, only: :create
        resource :feedback, only: :create
      end
    end
  end

  # Every other HTML route belongs to the Vue web app.
  get "*path", to: "spa#show", constraints: ->(req) { req.format.html? && !req.path.start_with?("/api/", "/cable", "/rails/") }
end
