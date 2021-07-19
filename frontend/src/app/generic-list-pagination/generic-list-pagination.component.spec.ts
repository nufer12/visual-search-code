import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { GenericListPaginationComponent } from './generic-list-pagination.component';

describe('GenericListPaginationComponent', () => {
  let component: GenericListPaginationComponent;
  let fixture: ComponentFixture<GenericListPaginationComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ GenericListPaginationComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(GenericListPaginationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
