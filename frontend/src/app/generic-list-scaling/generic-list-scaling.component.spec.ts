import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { GenericListScalingComponent } from './generic-list-scaling.component';

describe('GenericListScalingComponent', () => {
  let component: GenericListScalingComponent;
  let fixture: ComponentFixture<GenericListScalingComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ GenericListScalingComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(GenericListScalingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
