import { useNavigate } from 'react-router-dom'
import CompanyPanel from './CompanyPanel'

export default function CompaniesPage() {
  const navigate = useNavigate()

  const handleCompanySearch = (_ticker: string, name: string) => {
    navigate(`/?q=${encodeURIComponent(`What is ${name}'s pipeline and latest data?`)}`)
  }

  return (
    <div className="companies-page">
      <CompanyPanel onCompanySearch={handleCompanySearch} />
    </div>
  )
}
