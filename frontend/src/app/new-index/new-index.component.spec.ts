import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { NewIndexComponent } from './new-index.component';

describe('NewIndexComponent', () => {
  let component: NewIndexComponent;
  let fixture: ComponentFixture<NewIndexComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ NewIndexComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(NewIndexComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
