import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { TsneComponent } from './tsne.component';

describe('TsneComponent', () => {
  let component: TsneComponent;
  let fixture: ComponentFixture<TsneComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ TsneComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(TsneComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
