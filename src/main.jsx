import { createRoot } from 'react-dom/client'
import './index.css'
import App from './components/App/App.jsx'
import { ApiProvider } from './contexts/ApiContext.jsx'

createRoot(document.getElementById('root')).render(
  <ApiProvider>
      <App />
  </ApiProvider>
)
