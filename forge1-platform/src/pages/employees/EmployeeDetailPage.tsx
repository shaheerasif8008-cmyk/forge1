import { useParams } from 'react-router-dom';

export default function EmployeeDetailPage() {
  const { id } = useParams();
  
  return (
    <div>
      <h1 className="text-3xl font-bold">Employee Details</h1>
      <p className="text-muted-foreground">Employee ID: {id}</p>
    </div>
  );
}
