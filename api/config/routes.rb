Rails.application.routes.draw do
  # Health check for kamal-proxy and uptime monitors.
  get "up" => "rails/health#show", as: :rails_health_check

  # The web app's shell, never cached (see SpaController).
  root "spa#show"
  get "sw.js", to: "service_worker#show", format: false
  get "admin", to: "research_console#show"
  get "admin/data", to: "research_console#data"
  get "admin/cycles", to: "research_console#cycles"
  get "admin/cycles/ledger", to: "research_console#ledger"
  get "admin/uploads", to: "research_console#uploads"

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
      resource :me, only: %i[show update destroy], controller: "me"
      post "me/eligibility", to: "eligibility#create", as: :eligibility
      resources :error_log, only: %i[index show create update], controller: "error_log" do
        get :question, on: :member
        delete :question, on: :member, action: :acknowledge_question
      end
      resources :items, only: %i[index show] do
        resources :attempts, only: :create
        resource :feedback, only: :create
        resource :save, only: %i[update destroy], controller: "saved_items"
      end
      get "review", to: "review#index"
      get "config", to: "config#show"
      get "recommendations", to: "recommendations#index"
      namespace :research do
        resources :cycles, only: :create
        resources :memory_cycles, only: :show
        post "worker/lease", to: "worker#lease"
        post "worker/heartbeat", to: "worker#heartbeat"
        post "worker/:id/candidate", to: "worker#candidate"
        post "worker/:id/report", to: "worker#report"
        post "worker/:id/failure", to: "worker#failure"
      end
      namespace :auth do
        post "facebook", to: "facebook#create"
        post "facebook/data_deletion", to: "facebook#data_deletion"
      end
    end
  end

  # Every other page address belongs to the Vue web app, whatever the Accept header: crawlers
  # (Facebook's included) ask with */*. Paths with a file extension are files, so a missing one
  # stays a 404 instead of becoming the app shell.
  get "*path", to: "spa#show", format: false,
               constraints: ->(req) { !req.path.start_with?("/api/", "/cable", "/rails/") && File.extname(req.path).empty? }
end
