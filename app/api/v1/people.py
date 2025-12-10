from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Any
from uuid import UUID

from app.api import deps
from app.db.models.people import Supplier, Customer, Employee
from app.schemas import people as schemas

router = APIRouter()

# --- Suppliers ---

@router.get("/suppliers", response_model=List[schemas.Supplier])
async def read_suppliers(
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve suppliers.
    """
    result = await db.execute(
        select(Supplier)
        .filter(Supplier.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.post("/suppliers", response_model=schemas.Supplier)
async def create_supplier(
    *,
    db: AsyncSession = Depends(deps.get_db),
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
    await db.commit()
    await db.refresh(supplier)
    return supplier

@router.put("/suppliers/{supplier_id}", response_model=schemas.Supplier)
async def update_supplier(
    *,
    db: AsyncSession = Depends(deps.get_db),
    supplier_id: UUID,
    supplier_in: schemas.SupplierUpdate,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Update a supplier.
    """
    result = await db.execute(select(Supplier).filter(Supplier.id == supplier_id, Supplier.user_id == current_user.id))
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    update_data = supplier_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)
        
    # db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier

@router.delete("/suppliers/{supplier_id}", response_model=schemas.Supplier)
async def delete_supplier(
    *,
    db: AsyncSession = Depends(deps.get_db),
    supplier_id: UUID,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Delete a supplier.
    """
    result = await db.execute(select(Supplier).filter(Supplier.id == supplier_id, Supplier.user_id == current_user.id))
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    await db.delete(supplier)
    await db.commit()
    return supplier

# --- Customers ---

@router.get("/customers", response_model=List[schemas.Customer])
async def read_customers(
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve customers.
    """
    result = await db.execute(
        select(Customer)
        .filter(Customer.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.post("/customers", response_model=schemas.Customer)
async def create_customer(
    *,
    db: AsyncSession = Depends(deps.get_db),
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
    await db.commit()
    await db.refresh(customer)
    return customer

@router.put("/customers/{customer_id}", response_model=schemas.Customer)
async def update_customer(
    *,
    db: AsyncSession = Depends(deps.get_db),
    customer_id: UUID,
    customer_in: schemas.CustomerUpdate,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Update a customer.
    """
    result = await db.execute(select(Customer).filter(Customer.id == customer_id, Customer.user_id == current_user.id))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    update_data = customer_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
        
    # db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer

@router.delete("/customers/{customer_id}", response_model=schemas.Customer)
async def delete_customer(
    *,
    db: AsyncSession = Depends(deps.get_db),
    customer_id: UUID,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Delete a customer.
    """
    result = await db.execute(select(Customer).filter(Customer.id == customer_id, Customer.user_id == current_user.id))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    await db.delete(customer)
    await db.commit()
    return customer


# --- Employees ---

@router.get("/employees", response_model=List[schemas.Employee])
async def read_employees(
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve employees.
    """
    result = await db.execute(
        select(Employee)
        .filter(Employee.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.post("/employees", response_model=schemas.Employee)
async def create_employee(
    *,
    db: AsyncSession = Depends(deps.get_db),
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
    await db.commit()
    await db.refresh(employee)
    return employee

@router.put("/employees/{employee_id}", response_model=schemas.Employee)
async def update_employee(
    *,
    db: AsyncSession = Depends(deps.get_db),
    employee_id: UUID,
    employee_in: schemas.EmployeeUpdate,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Update an employee.
    """
    result = await db.execute(select(Employee).filter(Employee.id == employee_id, Employee.user_id == current_user.id))
    employee = result.scalars().first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    update_data = employee_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)
        
    # db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return employee

@router.delete("/employees/{employee_id}", response_model=schemas.Employee)
async def delete_employee(
    *,
    db: AsyncSession = Depends(deps.get_db),
    employee_id: UUID,
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Delete an employee.
    """
    result = await db.execute(select(Employee).filter(Employee.id == employee_id, Employee.user_id == current_user.id))
    employee = result.scalars().first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await db.delete(employee)
    await db.commit()
    return employee
