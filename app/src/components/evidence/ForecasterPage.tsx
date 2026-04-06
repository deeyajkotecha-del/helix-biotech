import { useNavigate } from 'react-router-dom'
import TrialForecasterPanel from './TrialForecasterPanel'

export default function ForecasterPage() {
  const navigate = useNavigate()

  const handleTrialSearch = (query: string) => {
    navigate(`/?q=${encodeURIComponent(query)}`)
  }

  return (
    <div className="forecaster-page">
      <TrialForecasterPanel onTrialSearch={handleTrialSearch} />
    </div>
  )
}
