Rails.application.routes.draw do
  # Health check for kamal-proxy and uptime monitors.
  get "up" => "rails/health#show", as: :rails_health_check

  namespace :api do
    namespace :v1 do
      resources :devices, only: :create
      resources :generations, only: %i[create show]
      resources :items, only: :show do
        resources :attempts, only: :create
      end
    end
  end
end
