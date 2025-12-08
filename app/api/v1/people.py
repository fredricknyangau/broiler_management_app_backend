from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from uuid import UUID

from app.api import deps
from app.db.models.people import Supplier, Customer, Employee
from app.schemas import people as schemas

router = APIRouter()

# --- Suppliers ---

@router.get("/suppliers", response_model=List[schemas.Supplier])
def read_suppliers(
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve suppliers.
    """
    suppliers = db.query(Supplier).filter(Supplier.user_id == current_user.id).offset(skip).limit(limit).all()
    return suppliers

@router.post("/suppliers", response_model=schemas.Supplier)
def create_supplier(
    *,
    db: Session = Depends(deps.get_db),
    supplier_in: schemas.SupplierCreate,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Create new supplier.
    """
    supplier = Supplier(
        **supplier_in.model_dump(),
        user_id=current_user.id
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

@router.put("/suppliers/{supplier_id}", response_model=schemas.Supplier)
def update_supplier(
    *,
    db: Session = Depends(deps.get_db),
    supplier_id: UUID,
    supplier_in: schemas.SupplierUpdate,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Update a supplier.
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id, Supplier.user_id == current_user.id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    update_data = supplier_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)
        
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

@router.delete("/suppliers/{supplier_id}", response_model=schemas.Supplier)
def delete_supplier(
    *,
    db: Session = Depends(deps.get_db),
    supplier_id: UUID,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Delete a supplier.
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id, Supplier.user_id == current_user.id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    db.delete(supplier)
    db.commit()
    return supplier

# --- Customers ---

@router.get("/customers", response_model=List[schemas.Customer])
def read_customers(
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve customers.
    """
    customers = db.query(Customer).filter(Customer.user_id == current_user.id).offset(skip).limit(limit).all()
    return customers

@router.post("/customers", response_model=schemas.Customer)
def create_customer(
    *,
    db: Session = Depends(deps.get_db),
    customer_in: schemas.CustomerCreate,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Create new customer.
    """
    customer = Customer(
        **customer_in.model_dump(),
        user_id=current_user.id
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

@router.put("/customers/{customer_id}", response_model=schemas.Customer)
def update_customer(
    *,
    db: Session = Depends(deps.get_db),
    customer_id: UUID,
    customer_in: schemas.CustomerUpdate,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Update a customer.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.user_id == current_user.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    update_data = customer_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
        
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

@router.delete("/customers/{customer_id}", response_model=schemas.Customer)
def delete_customer(
    *,
    db: Session = Depends(deps.get_db),
    customer_id: UUID,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Delete a customer.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.user_id == current_user.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    db.delete(customer)
    db.commit()
    return customer


# --- Employees ---

@router.get("/employees", response_model=List[schemas.Employee])
def read_employees(
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve employees.
    """
    employees = db.query(Employee).filter(Employee.user_id == current_user.id).offset(skip).limit(limit).all()
    return employees

@router.post("/employees", response_model=schemas.Employee)
def create_employee(
    *,
    db: Session = Depends(deps.get_db),
    employee_in: schemas.EmployeeCreate,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Create new employee.
    """
    employee = Employee(
        **employee_in.model_dump(),
        user_id=current_user.id
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee

@router.put("/employees/{employee_id}", response_model=schemas.Employee)
def update_employee(
    *,
    db: Session = Depends(deps.get_db),
    employee_id: UUID,
    employee_in: schemas.EmployeeUpdate,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Update an employee.
    """
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    update_data = employee_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)
        
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee

@router.delete("/employees/{employee_id}", response_model=schemas.Employee)
def delete_employee(
    *,
    db: Session = Depends(deps.get_db),
    employee_id: UUID,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Delete an employee.
    """
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    db.delete(employee)
    db.commit()
    return employee
