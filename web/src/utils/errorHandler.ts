export const formatApiError = (error: any): string => {
  if (!error?.response?.data) {
    return error?.message || 'An unexpected error occurred';
  }

  const { detail } = error.response.data;
  
  if (!detail) {
    return 'An unexpected error occurred';
  }

  // Handle Pydantic validation errors (array of error objects)
  if (Array.isArray(detail)) {
    return detail.map((err: any) => {
      if (typeof err === 'object' && err.msg) {
        return err.msg;
      }
      return String(err);
    }).join(', ');
  }

  // Handle string error messages
  if (typeof detail === 'string') {
    return detail;
  }

  // Handle single error objects
  if (typeof detail === 'object' && detail.msg) {
    return detail.msg;
  }

  // Fallback for any other object types
  return JSON.stringify(detail);
};
