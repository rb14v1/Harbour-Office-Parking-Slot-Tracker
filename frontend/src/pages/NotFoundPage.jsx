import { Link } from 'react-router-dom';
import { EmptyState } from '../components/common.jsx';

export default function NotFoundPage() {
  return (
    <div className="login-page">
      <div className="card shadow-sm p-4 text-center" style={{ maxWidth: 420 }}>
        <EmptyState icon="bi-signpost-split" title="Page not found" message="The page you requested does not exist." />
        <Link to="/dashboard" className="btn btn-primary mt-2">Back to dashboard</Link>
      </div>
    </div>
  );
}
